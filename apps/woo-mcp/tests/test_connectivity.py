"""Offline fixtures only; no live credentials, store or Kubernetes access."""

import asyncio
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
from oauthlib.oauth1 import Client, SIGNATURE_HMAC_SHA256, SIGNATURE_TYPE_AUTH_HEADER

from woo_mcp.config import Config, Credentials
from woo_mcp.connectivity import run
from woo_mcp.woocommerce import WooClient, WooError, product_urls

SKU = "URUMI-DEMO-001"
CREDS = Credentials("TEST-ONLY-KEY", "TEST-ONLY-SECRET")
PRODUCT = {"id": 11, "name": "Urumi Demo Mug", "sku": SKU, "price": "499",
           "status": "publish", "stock_status": "instock"}


class ConfigurationTests(unittest.TestCase):
    def test_origins_queries(self):
        canonical, connection = product_urls(Config(), "Mug & tea/+₹")
        self.assertEqual(urlsplit(canonical).netloc, "store.urumi.test:8080")
        self.assertEqual(urlsplit(connection).netloc, "urumi-wordpress.urumi.svc.cluster.local")
        self.assertEqual(urlsplit(canonical).query, urlsplit(connection).query)
        self.assertEqual(parse_qs(urlsplit(connection).query)["sku"], ["Mug & tea/+₹"])

    def test_invalid_origins(self):
        for origin in ("http://user:pass@host", "http://host/path", "http://host?key=x", "https://host"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                Config(connection_origin=origin)

    def test_required_files(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Required credential files"):
                Credentials.from_directory(Path(directory))
            for name, text in (("consumer-key", "TEST-ONLY-KEY"), ("consumer-secret", "TEST-ONLY-SECRET")):
                (Path(directory) / name).write_text(text)
            credentials = Credentials.from_directory(Path(directory))
            self.assertEqual(credentials.consumer_key, CREDS.consumer_key)
            self.assertNotIn(CREDS.consumer_key, repr(credentials))
            (Path(directory) / "consumer-key").write_text("\n")
            with self.assertRaises(ValueError):
                Credentials.from_directory(Path(directory))


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, handler, config=None):
        async with WooClient(config or Config(), CREDS, transport=httpx.MockTransport(handler)) as client:
            return await client.lookup_product(SKU)

    async def test_exact_signature_host_and_normalization(self):
        seen = []
        def handler(request):
            seen.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.headers["host"], "store.urumi.test:8080")
            canonical, connection = product_urls(Config(), SKU)
            self.assertEqual(str(request.url), connection)
            for text in (CREDS.consumer_key, CREDS.consumer_secret, "oauth_"):
                self.assertNotIn(text, str(request.url))
            signer = Client(CREDS.consumer_key, client_secret=CREDS.consumer_secret,
                            signature_method=SIGNATURE_HMAC_SHA256,
                            signature_type=SIGNATURE_TYPE_AUTH_HEADER,
                            nonce="fixture-nonce", timestamp="1700000000")
            self.assertEqual(request.headers["authorization"], signer.sign(canonical, http_method="GET")[1]["Authorization"])
            self.assertIn('oauth_signature_method="HMAC-SHA256"', request.headers["authorization"])
            return httpx.Response(200, json=[{**PRODUCT, "billing": {"private": "discard"}}])
        with patch("oauthlib.oauth1.rfc5849.generate_nonce", return_value="fixture-nonce"), patch(
                "oauthlib.oauth1.rfc5849.generate_timestamp", return_value="1700000000"):
            self.assertEqual(await self.request(handler), PRODUCT)
        self.assertEqual(len(seen), 1)

    async def test_redirect_not_followed(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(302, headers={"Location": "http://untrusted.invalid/private"})
        with self.assertRaises(WooError) as result:
            await self.request(handler)
        self.assertEqual(result.exception.code, "WOO_CONFIGURATION_ERROR")
        self.assertEqual(result.exception.status, 302)
        self.assertEqual(len(calls), 1)

    async def test_status_errors_and_no_retry(self):
        for status, code in ((401, "WOO_AUTH_FAILED"), (403, "WOO_FORBIDDEN"),
                             (404, "NOT_FOUND"), (400, "WOO_REQUEST_REJECTED"), (500, "WOO_UPSTREAM_ERROR")):
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(status, text="PRIVATE-UPSTREAM-DIAGNOSTIC")
            with self.subTest(status=status), self.assertRaises(WooError) as result:
                await self.request(handler)
            self.assertEqual(str(result.exception), code)
            self.assertEqual(len(calls), 1)

    async def test_transport_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("PRIVATE-DIAGNOSTIC")
        with self.assertRaisesRegex(WooError, "^WOO_TIMEOUT$"):
            await self.request(handler)

    async def test_absolute_deadline(self):
        async def handler(request):
            await asyncio.sleep(1)
            return httpx.Response(200, json=[PRODUCT])
        with self.assertRaisesRegex(WooError, "^WOO_TIMEOUT$"):
            await self.request(handler, Config(deadline_seconds=0.01))

    async def test_unreachable(self):
        def handler(request):
            raise httpx.ConnectError("PRIVATE-DIAGNOSTIC")
        with self.assertRaisesRegex(WooError, "^WOO_UNREACHABLE$"):
            await self.request(handler)

    async def test_malformed_responses(self):
        for data in (None, {}, [], [PRODUCT, PRODUCT], [{**PRODUCT, "price": "NaN"}], [{**PRODUCT, "id": True}]):
            with self.subTest(data=data), self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
                await self.request(lambda request: httpx.Response(200, json=data))
        with self.assertRaisesRegex(WooError, "WOO_INVALID_RESPONSE"):
            await self.request(lambda request: httpx.Response(200, text="not json"))

    async def test_response_bound(self):
        with self.assertRaisesRegex(WooError, "WOO_RESPONSE_TOO_LARGE"):
            await self.request(lambda request: httpx.Response(200, content=b"x" * 65537))

    async def test_invalid_sku_makes_no_request(self):
        def handler(request):
            self.fail("Unexpected request")
        async with WooClient(Config(), CREDS, transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(WooError, "VALIDATION_ERROR"):
                await client.lookup_product("")

    async def test_entrypoint_sanitizes_exception(self):
        output = io.StringIO()
        with patch.object(Credentials, "from_directory", side_effect=ValueError("PRIVATE-DIAGNOSTIC")), contextlib.redirect_stdout(output):
            result = await run()
        self.assertEqual(result, 1)
        self.assertNotIn("PRIVATE-DIAGNOSTIC", output.getvalue())
        self.assertFalse(json.loads(output.getvalue())["authorization_supplied"])


if __name__ == "__main__":
    unittest.main()
