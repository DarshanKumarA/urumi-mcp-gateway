"""Offline create semantics. Dummy credentials and mock transport only."""

import asyncio
import json
import unittest
from unittest.mock import patch

import httpx
from oauthlib.oauth1 import Client, SIGNATURE_HMAC_SHA256, SIGNATURE_TYPE_AUTH_HEADER
from pydantic import ValidationError

from woo_mcp.config import Config
from woo_mcp.models import CreateProductInput
from woo_mcp.woocommerce import WooClient, WooError
from test_products import CREDS, PRODUCT, HEADERS

INPUT = {"name": "Urumi Demo Mug", "price": "499"}
CREATED = {**PRODUCT, "id": 19, "sku": "", "permalink": "http://store.urumi.test:8080/product/mock-created/"}
EMPTY = {"X-WP-Total": "0", "X-WP-TotalPages": "0"}


class CreateInputTests(unittest.TestCase):
    def test_defaults_trim_and_optional_sku(self):
        result = CreateProductInput(name="  Mug  ", price="0.00", sku="  DEMO  ")
        self.assertEqual(result.model_dump(), dict(name="Mug", price="0.00", sku="DEMO",
                                                  status="publish", stock_status="instock"))
        self.assertIsNone(CreateProductInput(**INPUT).sku)

    def test_prices(self):
        for price in ("0", "0.1", "001.20", "999999999.99"):
            self.assertEqual(CreateProductInput(name="Mug", price=price).price, price)
        for price in (-1, 499, 499.0, True, None, "-1", "NaN", "Infinity", "1e2", "1.001",
                      "1000000000", "999999999.999", "", " 1", ".50", "1."):
            with self.subTest(price=price), self.assertRaises(ValidationError):
                CreateProductInput(name="Mug", price=price)

    def test_name_and_sku_bounds(self):
        CreateProductInput(name="x" * 200, price="1", sku="x" * 64)
        for values in ({"name": " "}, {"name": "x" * 201}, {"name": 1},
                       {"sku": ""}, {"sku": " "}, {"sku": "x" * 65}, {"sku": 1}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                CreateProductInput.model_validate({**INPUT, **values})

    def test_status_stock_and_extras(self):
        for status in ("publish", "draft"):
            for stock in ("instock", "outofstock"):
                CreateProductInput(**INPUT, status=status, stock_status=stock)
        for values in ({"status": "pending"}, {"status": None}, {"stock_status": "onbackorder"},
                       {"stock_status": None}, {"metadata": {}}, {"type": "variable"},
                       {"description": "x"}, {"url": "http://invalid"}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                CreateProductInput.model_validate({**INPUT, **values})


class CreateClientTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, handler, values=None, config=None):
        self.calls = []
        def tracked(request):
            self.calls.append(request.method)
            return handler(request)
        async with WooClient(config or Config(), CREDS, transport=httpx.MockTransport(tracked)) as client:
            return await client.create_product(CreateProductInput.model_validate(values or INPUT))

    def assert_unknown(self, error, code):
        self.assertEqual(error.code, code)
        self.assertEqual(error.write_outcome, "unknown")
        self.assertIs(error.retry_safe, False)
        self.assertEqual(str(error), code + "; write_outcome=unknown; retry_safe=false")
        for private in ("PRIVATE", CREDS.consumer_key, CREDS.consumer_secret, "Authorization"):
            self.assertNotIn(private, str(error))

    async def test_exact_payload_signing_and_normalization(self):
        def handler(request):
            self.assertEqual(request.method, "POST")
            self.assertEqual(str(request.url), "http://urumi-wordpress.urumi.svc.cluster.local/wp-json/wc/v3/products")
            self.assertEqual(request.headers["host"], "store.urumi.test:8080")
            self.assertEqual(request.headers["content-type"], "application/json")
            self.assertEqual(json.loads(request.content), {"name": INPUT["name"], "type": "simple",
                             "regular_price": "499", "status": "publish", "stock_status": "instock"})
            signer = Client(CREDS.consumer_key, client_secret=CREDS.consumer_secret,
                            signature_method=SIGNATURE_HMAC_SHA256, signature_type=SIGNATURE_TYPE_AUTH_HEADER,
                            nonce="fixture-nonce", timestamp="1700000000")
            expected = signer.sign("http://store.urumi.test:8080/wp-json/wc/v3/products", http_method="POST",
                                   headers={"Content-Type": "application/json"})[1]["Authorization"]
            self.assertEqual(request.headers["authorization"], expected)
            for secret in (CREDS.consumer_key, CREDS.consumer_secret, "oauth_"):
                self.assertNotIn(secret, str(request.url))
                self.assertNotIn(secret, request.content.decode())
            return httpx.Response(201, json={**CREATED, "private": "PRIVATE-BODY", "meta_data": [CREDS.consumer_key]})
        with patch("oauthlib.oauth1.rfc5849.generate_nonce", return_value="fixture-nonce"), patch(
                "oauthlib.oauth1.rfc5849.generate_timestamp", return_value="1700000000"):
            result = await self.request(handler)
        self.assertEqual(result.model_dump(), {"created": True, "product": {**CREATED, "currency": "INR"}})
        self.assertEqual(self.calls, ["POST"])

    async def test_sku_precheck_no_match_then_one_post(self):
        values = {**INPUT, "sku": "NEW-SKU", "status": "draft", "stock_status": "outofstock"}
        def handler(request):
            if request.method == "GET":
                self.assertEqual(request.url.path, "/wp-json/wc/v3/products")
                self.assertEqual(request.url.params["sku"], "NEW-SKU")
                self.assertEqual(request.url.params["per_page"], "1")
                self.assertNotIn("status", request.url.params)
                return httpx.Response(200, json=[], headers=EMPTY)
            self.assertEqual(json.loads(request.content), {"name": INPUT["name"], "type": "simple",
                "regular_price": "499", "status": "draft", "stock_status": "outofstock", "sku": "NEW-SKU"})
            return httpx.Response(201, json={**CREATED, "sku": "NEW-SKU", "status": "draft", "stock_status": "outofstock"})
        result = await self.request(handler, values)
        self.assertTrue(result.created)
        self.assertEqual(self.calls, ["GET", "POST"])

    async def test_null_sku_omitted(self):
        def handler(request):
            self.assertNotIn("sku", json.loads(request.content))
            return httpx.Response(201, json=CREATED)
        await self.request(handler, {**INPUT, "sku": None})
        self.assertEqual(self.calls, ["POST"])

    async def test_precheck_duplicate_never_posts(self):
        with self.assertRaisesRegex(WooError, "^DUPLICATE_SKU$"):
            await self.request(lambda r: httpx.Response(200, json=[PRODUCT], headers=HEADERS),
                               {**INPUT, "sku": PRODUCT["sku"]})
        self.assertEqual(self.calls, ["GET"])

    async def test_precheck_failure_never_posts(self):
        for status in (401, 500):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(status, text="PRIVATE"), {**INPUT, "sku": "NEW"})
            self.assertIsNone(raised.exception.write_outcome)
            self.assertEqual(self.calls, ["GET"])
        with self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
            await self.request(lambda r: httpx.Response(200, json=[]), {**INPUT, "sku": "NEW"})
        self.assertEqual(self.calls, ["GET"])

    async def test_create_time_conflict(self):
        for status in (400, 409):
            def handler(request):
                if request.method == "GET":
                    return httpx.Response(200, json=[], headers=EMPTY)
                return httpx.Response(status, json={"code": "product_invalid_sku", "message": "PRIVATE", "data": CREDS.consumer_key})
            with self.assertRaisesRegex(WooError, "^DUPLICATE_SKU$"):
                await self.request(handler, {**INPUT, "sku": "NEW"})
            self.assertEqual(self.calls, ["GET", "POST"])

    async def test_conflict_is_not_message_guessing(self):
        with self.assertRaisesRegex(WooError, "^WOO_REQUEST_REJECTED$"):
            await self.request(lambda r: httpx.Response(400, json={"code": "different", "message": "product_invalid_sku"}))
        self.assertEqual(self.calls, ["POST"])

    async def test_rejected_statuses(self):
        for status, code in ((401, "WOO_AUTH_FAILED"), (403, "WOO_FORBIDDEN"), (404, "NOT_FOUND"),
                             (422, "WOO_REQUEST_REJECTED"), (429, "WOO_REQUEST_REJECTED")):
            with self.assertRaisesRegex(WooError, "^"+code+"$"):
                await self.request(lambda r: httpx.Response(status, text="PRIVATE"))
            self.assertEqual(self.calls, ["POST"])

    async def test_network_failures_are_unknown_once(self):
        for exception, code in ((httpx.ReadTimeout("PRIVATE"), "WOO_TIMEOUT"),
                                (httpx.WriteTimeout("PRIVATE"), "WOO_TIMEOUT"),
                                (httpx.ConnectError("PRIVATE"), "WOO_UNREACHABLE"),
                                (httpx.ReadError("PRIVATE"), "WOO_UNREACHABLE")):
            def handler(request):
                raise exception
            with self.assertRaises(WooError) as raised:
                await self.request(handler)
            self.assert_unknown(raised.exception, code)
            self.assertEqual(self.calls, ["POST"])

    async def test_sku_timeout_no_reconciliation_read(self):
        def handler(request):
            if request.method == "GET":
                return httpx.Response(200, json=[], headers=EMPTY)
            raise httpx.ReadTimeout("PRIVATE")
        with self.assertRaises(WooError) as raised:
            await self.request(handler, {**INPUT, "sku": "NEW"})
        self.assert_unknown(raised.exception, "WOO_TIMEOUT")
        self.assertEqual(self.calls, ["GET", "POST"])

    async def test_write_committed_but_response_body_lost(self):
        committed = []
        class LostResponse(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'{"id":19,'
                raise httpx.ReadError("PRIVATE lost response after commit")
        def handler(request):
            committed.append(json.loads(request.content))
            return httpx.Response(201, stream=LostResponse())
        with self.assertRaises(WooError) as raised:
            await self.request(handler)
        self.assert_unknown(raised.exception, "WOO_UNREACHABLE")
        self.assertEqual(len(committed), 1)
        self.assertEqual(self.calls, ["POST"])

    async def test_server_redirect_unexpected_success_are_unknown(self):
        for status, code in ((500, "WOO_UPSTREAM_ERROR"), (503, "WOO_UPSTREAM_ERROR"),
                             (408, "WOO_REQUEST_REJECTED"), (302, "WOO_CONFIGURATION_ERROR"),
                             (200, "WOO_INVALID_RESPONSE"), (202, "WOO_INVALID_RESPONSE")):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(status, text="PRIVATE", headers={"Location": "http://invalid"}))
            self.assert_unknown(raised.exception, code)
            self.assertEqual(self.calls, ["POST"])

    async def test_bad_response_is_unknown(self):
        for data in (None, [], {}, {**CREATED, "id": "19"}, {**CREATED, "regular_price": "500"},
                     {**CREATED, "type": "variable"}, {**CREATED, "stock_status": "outofstock"}):
            with self.assertRaises(WooError) as raised:
                await self.request(lambda r: httpx.Response(201, json=data))
            self.assert_unknown(raised.exception, "WOO_INVALID_RESPONSE")
            self.assertEqual(self.calls, ["POST"])

    async def test_bad_json_and_size_are_unknown(self):
        for status in (201, 400):
            for body, code in ((b"PRIVATE invalid JSON", "WOO_INVALID_RESPONSE"),
                               (b"x" * 65537, "WOO_RESPONSE_TOO_LARGE")):
                with self.assertRaises(WooError) as raised:
                    await self.request(lambda r: httpx.Response(status, content=body))
                self.assert_unknown(raised.exception, code)
                self.assertEqual(self.calls, ["POST"])

    async def test_absolute_deadline_no_retry(self):
        async def handler(request):
            await asyncio.sleep(1)
        with self.assertRaises(WooError) as raised:
            await self.request(handler, config=Config(deadline_seconds=0.01))
        self.assert_unknown(raised.exception, "WOO_TIMEOUT")
        self.assertEqual(self.calls, ["POST"])

    async def test_cancellation_does_not_replay(self):
        def handler(request):
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.request(handler)
        self.assertEqual(self.calls, ["POST"])

    async def test_unexpected_transport_failure_safe_unknown(self):
        def handler(request):
            raise RuntimeError("PRIVATE request header")
        with self.assertRaises(WooError) as raised:
            await self.request(handler)
        self.assert_unknown(raised.exception, "WOO_INTERNAL_ERROR")
        self.assertEqual(self.calls, ["POST"])
