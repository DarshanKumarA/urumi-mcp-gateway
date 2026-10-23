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
            self.assertEqual([tool.name for tool in tools], ["list_products"])
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
