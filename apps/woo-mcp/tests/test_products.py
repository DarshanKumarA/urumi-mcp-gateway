"""List-products contracts and real client mapping with mocked REST only."""

import asyncio
import unittest

import httpx
from pydantic import ValidationError

from woo_mcp.config import Config, Credentials
from woo_mcp.models import ListProductsInput, ProductCollection
from woo_mcp.woocommerce import WooClient, WooError

CREDS = Credentials("TEST-ONLY-KEY", "TEST-ONLY-SECRET")
PRODUCT = {"id": 11, "name": "Urumi Demo Mug", "sku": "URUMI-DEMO-001", "type": "simple",
           "price": "499", "regular_price": "499", "status": "publish", "stock_status": "instock",
           "permalink": "http://store.urumi.test:8080/product/urumi-demo-mug/"}
HEADERS = {"X-WP-Total": "1", "X-WP-TotalPages": "1"}


class InputTests(unittest.TestCase):
    def test_currency_configuration(self):
        for currency in ("inr", "A1R", "IN", "ÄBC"):
            with self.subTest(currency=currency), self.assertRaises(ValueError):
                Config(currency=currency)

    def test_defaults_and_trim(self):
        self.assertEqual(ListProductsInput().model_dump(),
                         dict(page=1, per_page=20, search=None, sku=None, status=None))
        self.assertEqual(ListProductsInput(search="  Mug  ").search, "Mug")
        self.assertEqual(ListProductsInput(sku=" A ").sku, "A")

    def test_invalid_inputs(self):
        for value in ({"page": True}, {"page": "1"}, {"page": 1.0}, {"page": 0},
                      {"per_page": 51}, {"per_page": 0}, {"search": " "}, {"search": "x" * 101},
                      {"sku": "x" * 65}, {"status": "trash"}, {"url": "http://invalid"},
                      {"search": "a", "sku": "b"}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ListProductsInput.model_validate(value)


class ProductTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, handler, query=None, config=None):
        async with WooClient(config or Config(), CREDS, transport=httpx.MockTransport(handler)) as client:
            return await client.list_products(query or ListProductsInput())

    async def test_mapping_normalization(self):
        calls = []
        def handler(request):
            calls.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/wp-json/wc/v3/products")
            self.assertEqual(request.url.host, "urumi-wordpress.urumi.svc.cluster.local")
            self.assertEqual(request.headers["host"], "store.urumi.test:8080")
            self.assertEqual(request.url.params["search"], "Mug & tea/+₹")
            self.assertEqual(request.url.params["page"], "2")
            self.assertEqual(request.url.params["per_page"], "1")
            self.assertEqual(request.url.params["status"], "publish")
            self.assertEqual(set(request.url.params), {"page", "per_page", "search", "status", "_fields"})
            self.assertNotIn(CREDS.consumer_key, str(request.url))
            self.assertNotIn(CREDS.consumer_secret, str(request.url))
            return httpx.Response(200, json=[{**PRODUCT, "private": "PRIVATE-RESPONSE"}],
                                  headers={"X-WP-Total": "3", "X-WP-TotalPages": "3"})
        result = await self.request(handler, ListProductsInput(page=2, per_page=1, search="Mug & tea/+₹", status="publish"))
        self.assertIsInstance(result, ProductCollection)
        self.assertTrue(result.has_more)
        self.assertEqual(result.currency, "INR")
        self.assertEqual(result.items[0].model_dump(), {**PRODUCT, "currency": "INR"})
        for private in ("PRIVATE-RESPONSE", CREDS.consumer_key, CREDS.consumer_secret):
            self.assertNotIn(private, result.model_dump_json())
        self.assertEqual(len(calls), 1)

    async def test_sku_last_page(self):
        def handler(request):
            self.assertEqual(request.url.params["sku"], "URUMI-DEMO-001")
            return httpx.Response(200, json=[PRODUCT], headers=HEADERS)
        self.assertFalse((await self.request(handler, ListProductsInput(sku="URUMI-DEMO-001"))).has_more)

    async def test_empty_collection(self):
        result = await self.request(lambda r: httpx.Response(200, json=[],
            headers={"X-WP-Total": "0", "X-WP-TotalPages": "0"}))
        self.assertEqual(result.items, [])
        self.assertFalse(result.has_more)

    async def test_draft_without_price(self):
        result = await self.request(lambda r: httpx.Response(200,
            json=[{**PRODUCT, "status": "draft", "price": "", "regular_price": ""}], headers=HEADERS))
        self.assertEqual(result.items[0].price, "")

    async def test_bad_pagination(self):
        for headers in ({}, {**HEADERS, "X-WP-Total": "-1"}, {**HEADERS, "X-WP-Total": "1.0"},
                        {**HEADERS, "X-WP-TotalPages": "2"}, {**HEADERS, "X-WP-Total": "2"},
                        [("X-WP-Total", "1"), ("X-WP-Total", "1"), ("X-WP-TotalPages", "1")]):
            with self.subTest(headers=headers), self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
                await self.request(lambda r: httpx.Response(200, json=[PRODUCT], headers=headers))

    async def test_malformed_product(self):
        for data in ({}, [None], [{**PRODUCT, "id": "11"}], [{**PRODUCT, "regular_price": "NaN"}],
                     [{**PRODUCT, "permalink": "javascript:alert(1)"}], [{}]):
            with self.subTest(data=data), self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
                await self.request(lambda r: httpx.Response(200, json=data, headers=HEADERS))

    async def test_http_errors(self):
        for status, code in ((401, "WOO_AUTH_FAILED"), (403, "WOO_FORBIDDEN"),
                             (404, "NOT_FOUND"), (422, "WOO_REQUEST_REJECTED"), (500, "WOO_UPSTREAM_ERROR"),
                             (302, "WOO_CONFIGURATION_ERROR")):
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(status, text="PRIVATE-RESPONSE", headers={"Location": "http://invalid"})
            with self.subTest(status=status), self.assertRaisesRegex(WooError, "^" + code + "$"):
                await self.request(handler)
            self.assertEqual(len(calls), 1)

    async def test_transport_failures(self):
        for exception, code in ((httpx.ConnectError("PRIVATE"), "WOO_UNREACHABLE"),
                                (httpx.ReadTimeout("PRIVATE"), "WOO_TIMEOUT")):
            def handler(request):
                raise exception
            with self.subTest(code=code), self.assertRaisesRegex(WooError, code):
                await self.request(handler)

    async def test_json_and_size(self):
        for body, code in ((b"not json", "WOO_INVALID_RESPONSE"), (b"x" * 65537, "WOO_RESPONSE_TOO_LARGE")):
            with self.subTest(code=code), self.assertRaisesRegex(WooError, code):
                await self.request(lambda r: httpx.Response(200, content=body, headers=HEADERS))

    async def test_deadline(self):
        async def handler(request):
            await asyncio.sleep(1)
        with self.assertRaisesRegex(WooError, "WOO_TIMEOUT"):
            await self.request(handler, config=Config(deadline_seconds=0.01))
