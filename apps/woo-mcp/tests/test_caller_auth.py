"""Synthetic service token only; no live REST requests."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from woo_mcp.caller_auth import CallerAuthentication
from woo_mcp.server import create_server
from test_products import CREDS
from woo_mcp.config import Config
from woo_mcp.woocommerce import WooClient
import httpx

TOKEN = "SYNTHETIC-CALLER-" + "x" * 40


class CallerAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urumi-caller-")
        self.path = Path(self.directory.name) / "token"
        self.path.write_text(TOKEN)
        self.env = patch.dict(os.environ, {"WOO_MCP_AUTH_TOKEN_FILE": str(self.path)})
        self.env.start()

    async def asyncTearDown(self):
        self.env.stop()
        self.directory.cleanup()

    async def test_every_http_method_denies_missing_invalid_duplicate_and_query(self):
        called = []
        async def inner(scope, receive, send):
            called.append(scope)
        app = CallerAuthentication(inner)
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://localhost") as http:
            for method in ("GET", "POST", "DELETE", "OPTIONS"):
                for headers in ({}, {"Authorization": "Basic invalid"}, {"Authorization": "Bearer invalid"},
                                [("Authorization", "Bearer " + TOKEN)] * 2):
                    r = await http.request(method, "/mcp?token=invalid", headers=headers)
                    self.assertEqual(r.status_code, 401)
                    self.assertEqual(r.headers["www-authenticate"], "Bearer")
                    self.assertNotIn(TOKEN, r.text)
            self.assertEqual(called, [])

    async def test_valid_request_strips_service_credential(self):
        seen = []
        async def inner(scope, receive, send):
            from starlette.responses import Response
            seen.extend(scope["headers"])
            await Response()(scope, receive, send)
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=CallerAuthentication(inner))) as http:
            self.assertEqual((await http.get("http://127.0.0.1:8000/mcp", headers={"Authorization": "Bearer " + TOKEN})).status_code, 200)
        self.assertFalse(any(k == b"authorization" for k, _ in seen))

    async def test_missing_or_malformed_file_fails_closed(self):
        for value in ("", "short", "bad\n" + TOKEN, "x" * 256 + "\ntrailing"):
            self.path.write_text(value)
            with self.assertRaisesRegex(ValueError, "^CALLER_AUTH_CONFIGURATION_INVALID$"):
                CallerAuthentication(None)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "^CALLER_AUTH_CONFIGURATION_INVALID$"):
            CallerAuthentication(None)

    async def test_authenticated_current_and_legacy_discovery_no_woo_call(self):
        calls = []
        def trap(request):
            calls.append(request)
            raise AssertionError("No business request authorized")
        for mode in ("2026-07-28", "legacy"):
            app = create_server(client_factory=lambda: WooClient(Config(), CREDS,
                transport=httpx.MockTransport(trap))).streamable_http_app(
                    streamable_http_path="/mcp", json_response=True, stateless_http=True)
            app.add_middleware(CallerAuthentication)
            async with app.router.lifespan_context(app):
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                    headers={"Authorization": "Bearer " + TOKEN}) as http:
                    async with Client(streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http), mode=mode) as client:
                        self.assertEqual(len((await client.list_tools()).tools), 5)
                    r = await http.get("http://127.0.0.1:8000/mcp", headers={"Authorization": "Bearer invalid"})
                    self.assertEqual(r.status_code, 401)
        self.assertEqual(calls, [])
