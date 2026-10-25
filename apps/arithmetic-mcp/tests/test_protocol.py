"""Official clients over actual SDK ASGI transports; no outbound service."""
import asyncio
import os
import unittest
from unittest.mock import patch
import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from arithmetic_mcp.server import create_app, allowed_hosts


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, mode):
        app = create_app()
        async with asyncio.timeout(15):
            async with app.router.lifespan_context(app):
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), trust_env=False) as http:
                    async with Client(streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http), mode=mode, cache=None) as client:
                        tools = (await client.list_tools()).tools
                        self.assertEqual([t.name for t in tools], ["sum_amounts"])
                        tool = tools[0]
                        self.assertFalse(tool.input_schema["additionalProperties"])
                        self.assertEqual(set(tool.input_schema["properties"]), {'amounts', 'currency'})
                        self.assertEqual(set(tool.output_schema["properties"]), {'count','total','average','minimum','maximum','currency'})
                        self.assertTrue(tool.annotations.read_only_hint)
                        self.assertTrue(tool.annotations.idempotent_hint)
                        self.assertFalse(tool.annotations.destructive_hint)
                        self.assertEqual(tool.input_schema["properties"]["amounts"]["maxItems"], 100)
                        result = await client.session.call_tool("sum_amounts", {'amounts':['1.25','2.75'],'currency':'INR'})
                        self.assertFalse(result.is_error)
                        self.assertEqual(result.structured_content["total"], '4')
                        for bad in [{'amounts':[1.2]}, {'amounts':[]}, {'amounts':['PRIVATE_SENTINEL']}, {'amounts':['1'],'PRIVATE_SENTINEL':True}, {'amounts':'[1]'}]:
                            rejected = await client.session.call_tool("sum_amounts", bad)
                            self.assertTrue(rejected.is_error)
                            self.assertIn("VALIDATION_ERROR", rejected.content[0].text)
                            self.assertNotIn("PRIVATE_SENTINEL", rejected.model_dump_json())

    async def test_current_protocol(self):
        await self.check("2026-07-28")

    async def test_legacy_protocol(self):
        await self.check("legacy")

    async def test_auto_protocol(self):
        await self.check("auto")

    async def test_host_and_origin_protection(self):
        app = create_app()
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), trust_env=False) as http:
                with patch("mcp.server.transport_security.logger"):
                    self.assertEqual((await http.get("http://127.0.0.1:8000/mcp", headers={"Host": "evil.invalid"})).status_code, 421)
                    r = await http.get("http://127.0.0.1:8000/mcp", headers={"Origin": "http://browser.invalid"})
                    self.assertEqual(r.status_code, 403)
                    self.assertNotIn("access-control-allow-origin", r.headers)

    async def test_config_exact_hosts_and_rejection(self):
        hosts = ["urumi-arithmetic-mcp", "urumi-arithmetic-mcp.urumi", "urumi-arithmetic-mcp.urumi.svc", "urumi-arithmetic-mcp.urumi.svc.cluster.local"]
        hosts = [h + port for h in hosts for port in ("", ":8000")]
        with patch.dict(os.environ, {"MCP_ALLOWED_HOSTS": ",".join(hosts)}):
            self.assertEqual(allowed_hosts(), hosts)
        for bad in ("", "*", "http://bad", "localhost:65536", "localhost,localhost", "bad PRIVATE_SENTINEL"):
            with patch.dict(os.environ, {"MCP_ALLOWED_HOSTS": bad}), self.assertRaisesRegex(ValueError, "^INVALID_HOST_CONFIGURATION$"):
                allowed_hosts()
