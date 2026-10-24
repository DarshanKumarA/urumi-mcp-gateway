"""Official SDK client -> Streamable HTTP /mcp ASGI -> real client/mock REST."""

import asyncio
import unittest
from contextlib import asynccontextmanager

import httpx
import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

from woo_mcp.config import Config
from woo_mcp.server import create_server
from woo_mcp.woocommerce import WooClient
from test_products import CREDS, PRODUCT, HEADERS
from test_orders import ORDER, PRIVATE, assert_private_absent
from test_create_product import CREATED, EMPTY, INPUT


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def connection(self, mode="auto", handler=None):
        self.clients = []
        self.requests = []
        self.responses = []
        self.rest_calls = []

        def rest(request):
            self.rest_calls.append(request)
            return handler(request) if handler else httpx.Response(200, json=[PRODUCT], headers=HEADERS)

        def factory():
            client = WooClient(Config(), CREDS, transport=httpx.MockTransport(rest))
            self.clients.append(client)
            return client

        async def record_request(request):
            self.requests.append((request.url.path, dict(request.headers)))

        async def record_response(response):
            self.responses.append(dict(response.headers))

        server = create_server(client_factory=factory)
        app = server.streamable_http_app(streamable_http_path="/mcp", json_response=True, stateless_http=True)
        async with asyncio.timeout(15):
            async with app.router.lifespan_context(app):
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), trust_env=False,
                    event_hooks={"request": [record_request], "response": [record_response]}) as http:
                    transport = streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http)
                    async with Client(transport, mode=mode, cache=None) as client:
                        yield client
        self.assertEqual(len(self.clients), 1)
        self.assertTrue(self.clients[0]._http.is_closed)

    async def check_protocol(self, mode):
        async with self.connection(mode) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual([tool.name for tool in tools], ["list_products", "get_order", "list_orders", "create_product"])
            self.assertTrue(all(t.annotations.read_only_hint for t in tools[:3]))
            self.assertFalse(tools[3].annotations.read_only_hint)
            self.assertFalse(tools[3].annotations.idempotent_hint)
            self.assertTrue(tools[3].annotations.destructive_hint)
            self.assertTrue(all(t.input_schema["additionalProperties"] is False for t in tools))
            schema = tools[0].input_schema
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(schema["properties"]["page"]["default"], 1)
            self.assertEqual(schema["properties"]["per_page"]["default"], 20)
            self.assertEqual(schema["properties"]["per_page"]["maximum"], 50)
            self.assertEqual(set(schema["properties"]), {"page", "per_page", "search", "sku", "status"})
            self.assertEqual(set(tools[0].output_schema["properties"]),
                             {"items", "page", "per_page", "total", "total_pages", "has_more", "currency"})
            self.assertTrue(tools[0].annotations.read_only_hint)
            for _ in range(2):
                result = await client.call_tool("list_products", {"sku": "URUMI-DEMO-001"})
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content["items"], [{**PRODUCT, "currency": "INR"}])
                self.assertFalse(result.structured_content["has_more"])
            self.assertEqual(len(self.rest_calls), 2)
            self.assertTrue(all(path == "/mcp" for path, _ in self.requests))
            self.assertTrue(all("mcp-session-id" not in headers for _, headers in self.requests))
            self.assertTrue(all("mcp-session-id" not in headers for headers in self.responses))
            versions = {h.get("mcp-protocol-version") for _, h in self.requests}
            self.assertIn("2025-11-25" if mode == "legacy" else "2026-07-28", versions)

    async def test_modern_discovery(self):
        await self.check_protocol("auto")

    async def test_explicit_2026(self):
        await self.check_protocol("2026-07-28")

    async def test_legacy_2025(self):
        await self.check_protocol("legacy")

    async def test_invalid_arguments_are_safe_tool_errors(self):
        async with self.connection() as client:
            for arguments in ({"page": "1"}, {"page": True}, {"per_page": 51},
                              {"status": "PRIVATE-REJECTED-VALUE"}, {"unknown": "PRIVATE-REJECTED-VALUE"},
                              {"search": " "}, {"search": "a", "sku": "b"}):
                with self.subTest(arguments=arguments):
                    result = await client.call_tool("list_products", arguments)
                    self.assertTrue(result.is_error)
                    self.assertIsNone(result.structured_content)
                    text = result.content[0].text
                    self.assertIn("VALIDATION_ERROR", text)
                    self.assertNotIn("PRIVATE-REJECTED-VALUE", text)
            self.assertEqual(len(self.rest_calls), 0)

    async def test_upstream_error_is_not_success(self):
        async with self.connection(handler=lambda r: httpx.Response(401, text="PRIVATE-RESPONSE")) as client:
            result = await client.call_tool("list_products", {})
            self.assertTrue(result.is_error)
            self.assertIsNone(result.structured_content)
            self.assertIn("WOO_AUTH_FAILED", result.content[0].text)
            self.assertNotIn("PRIVATE-RESPONSE", result.model_dump_json())
            self.assertNotIn(CREDS.consumer_key, result.model_dump_json())

    async def test_order_protocols(self):
        for mode in ("auto", "2026-07-28", "legacy"):
            def handler(request):
                return httpx.Response(200, json=ORDER if request.url.path.endswith("/12") else [ORDER],
                                      headers=HEADERS)
            async with self.connection(mode, handler) as client:
                tools = {t.name: t for t in (await client.list_tools()).tools}
                detail_schema = tools["get_order"].input_schema
                self.assertEqual(detail_schema["required"], ["order_id"])
                self.assertEqual(set(detail_schema["properties"]), {"order_id"})
                self.assertEqual(detail_schema["properties"]["order_id"]["exclusiveMinimum"], 0)
                listing = tools["list_orders"].input_schema
                self.assertEqual(set(listing["properties"]), {"page", "per_page", "status", "date"})
                self.assertEqual(listing["properties"]["page"]["default"], 1)
                self.assertEqual(listing["properties"]["per_page"]["maximum"], 50)
                self.assertEqual(set(tools["get_order"].output_schema["properties"]),
                                 {"id", "status", "created_at", "currency", "total", "payment_method",
                                  "line_items", "shipping_lines", "shipping_total", "tax_total"})
                for name, args in (("get_order", {"order_id": 12}),
                                   ("list_orders", {"date": "2026-10-21", "status": "processing"})):
                    result = await client.call_tool(name, args)
                    self.assertFalse(result.is_error)
                    assert_private_absent(self, result.model_dump_json())
                    if name == "get_order":
                        self.assertEqual(result.structured_content["id"], 12)
                        self.assertEqual(result.structured_content["line_items"][0]["product_id"], 11)
                    else:
                        self.assertEqual(result.structured_content["items"][0]["id"], 12)
                        self.assertEqual(result.structured_content["date_window"]["date"], "2026-10-21")
                        self.assertFalse(result.structured_content["has_more"])

    async def test_order_invalid_arguments(self):
        async with self.connection() as client:
            cases = {"get_order": ({}, {"order_id": 0}, {"order_id": -1}, {"order_id": True},
                                   {"order_id": "12"}, {"order_id": 12, "SYNTHETIC-PRIVATE": "secret"}),
                     "list_orders": ({"page": True}, {"per_page": 51}, {"status": "SYNTHETIC-PRIVATE"},
                                     {"date": "2026-02-30"}, {"date": "SYNTHETIC-PRIVATE"},
                                     {"unknown": "SYNTHETIC-PRIVATE"})}
            for name, arguments in cases.items():
                for args in arguments:
                    result = await client.call_tool(name, args)
                    self.assertTrue(result.is_error)
                    self.assertIsNone(result.structured_content)
                    self.assertIn("VALIDATION_ERROR", result.content[0].text)
                    assert_private_absent(self, result.model_dump_json())
            self.assertEqual(self.rest_calls, [])

    async def test_order_errors_are_sanitized(self):
        for status, code in ((404, "NOT_FOUND"), (401, "WOO_AUTH_FAILED"), (200, "WOO_INVALID_RESPONSE")):
            async with self.connection(handler=lambda r: httpx.Response(status, json=PRIVATE)) as client:
                for name, args in (("get_order", {"order_id": 12}), ("list_orders", {})):
                    result = await client.call_tool(name, args)
                    self.assertTrue(result.is_error)
                    self.assertIsNone(result.structured_content)
                    self.assertIn(code, result.content[0].text)
                    assert_private_absent(self, result.model_dump_json())

    async def test_create_protocols(self):
        for mode in ("auto", "2026-07-28", "legacy"):
            async with self.connection(mode, handler=lambda r: httpx.Response(201, json=CREATED)) as client:
                tools = {t.name: t for t in (await client.list_tools()).tools}
                tool = tools["create_product"]
                schema = tool.input_schema
                self.assertEqual(set(schema["required"]), {"name", "price"})
                self.assertEqual(set(schema["properties"]), {"name", "price", "sku", "status", "stock_status"})
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["properties"]["name"]["maxLength"], 200)
                self.assertEqual(schema["properties"]["price"]["type"], "string")
                self.assertEqual(schema["properties"]["status"]["enum"], ["publish", "draft"])
                self.assertEqual(schema["properties"]["status"]["default"], "publish")
                self.assertEqual(schema["properties"]["stock_status"]["default"], "instock")
                self.assertEqual(set(tool.output_schema["properties"]), {"product", "created"})
                result = await client.call_tool("create_product", INPUT)
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content, {"created": True, "product": {**CREATED, "currency": "INR"}})
                assert_private_absent(self, result.model_dump_json())
                self.assertEqual([r.method for r in self.rest_calls], ["POST"])

    async def test_create_validation(self):
        async with self.connection() as client:
            for args in ({}, {**INPUT, "name": " "}, {**INPUT, "price": 499.0},
                         {**INPUT, "price": "1000000000"}, {**INPUT, "status": "private"},
                         {**INPUT, "description": "SYNTHETIC-PRIVATE"}):
                result = await client.call_tool("create_product", args)
                self.assertTrue(result.is_error)
                self.assertIsNone(result.structured_content)
                self.assertIn("VALIDATION_ERROR", result.content[0].text)
                assert_private_absent(self, result.model_dump_json())
            self.assertEqual(self.rest_calls, [])

    async def test_create_duplicates_and_unknown_errors(self):
        for mode in ("auto", "legacy"):
            for kind in ("precheck", "race", "timeout", "server"):
                def handler(request):
                    if request.method == "GET":
                        return httpx.Response(200, json=[PRODUCT] if kind == "precheck" else [],
                                              headers=HEADERS if kind == "precheck" else EMPTY)
                    if kind == "race":
                        return httpx.Response(400, json={"code": "product_invalid_sku", "message": "SYNTHETIC-PRIVATE"})
                    if kind == "timeout":
                        raise httpx.ReadTimeout("SYNTHETIC-PRIVATE")
                    return httpx.Response(500, json=PRIVATE)
                async with self.connection(mode, handler) as client:
                    result = await client.call_tool("create_product", {**INPUT, "sku": PRODUCT["sku"]})
                    self.assertTrue(result.is_error)
                    self.assertIsNone(result.structured_content)
                    text = result.content[0].text
                    if kind in ("precheck", "race"):
                        self.assertIn("DUPLICATE_SKU", text)
                    else:
                        self.assertIn("write_outcome=unknown", text)
                        self.assertIn("retry_safe=false", text)
                    assert_private_absent(self, result.model_dump_json())
                    self.assertEqual([r.method for r in self.rest_calls],
                                     ["GET"] if kind == "precheck" else ["GET", "POST"])
