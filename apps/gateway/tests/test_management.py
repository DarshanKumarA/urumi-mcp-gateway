"""Real FastAPI + SQL repository + official MCP ASGI fixtures, no network/store calls."""
import unittest
import asyncio
from contextlib import AsyncExitStack
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

from urumi_gateway.api import create_app
from urumi_gateway.upstream import UpstreamClient
from urumi_gateway.database import RepositoryUnavailable
from support import SYNTHETIC, UpstreamFixture
from test_persistence import DatabaseFixture


class ManagementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseFixture()
        self.fixture = UpstreamFixture("server_a")
        upstream = UpstreamClient(transport_factory=lambda s: self.fixture.transport())
        self.app = create_app(self.db.repo, upstream=upstream)
        await self.app.state.identity.bootstrap_admin("fixture_admin", "synthetic-admin-password-only")
        self.started, self.stopped = asyncio.Event(), asyncio.Event()

        async def rest_origin(request):
            if request.url.path.startswith("/api/") and "origin" not in request.headers:
                request.headers["Origin"] = "http://127.0.0.1:8000"

        async def owner():
            # unittest setup/test/teardown use different tasks. SDK cancel scopes
            # must be entered/exited in the same task, like a real ASGI lifespan.
            async with AsyncExitStack() as stack:
                for app in (self.fixture.app, self.app):
                    await stack.enter_async_context(app.router.lifespan_context(app))
                self.http = await stack.enter_async_context(httpx2.AsyncClient(
                    base_url="http://127.0.0.1:8000", event_hooks={"request": [rest_origin]}, transport=httpx2.ASGITransport(app=self.app)))
                self.started.set()
                await self.stopped.wait()
        self.owner = asyncio.create_task(owner())
        await asyncio.wait_for(self.started.wait(), 5)
        login = await self.http.post("/api/auth/login", json={"username": "fixture_admin", "password": "synthetic-admin-password-only"})
        self.assertEqual(login.status_code, 200)
        response = await self.http.post("/api/servers", json={"slug": "server_a", "display_name": "A",
            "url": "http://127.0.0.1:9001/mcp", "credential": {"kind": "bearer", "value": SYNTHETIC}})
        self.assertEqual(response.status_code, 201)
        self.id = response.json()["id"]
        self.path = "/api/servers/" + self.id

    async def asyncTearDown(self):
        self.stopped.set()
        try:
            await self.owner
        finally:
            self.db.close()

    async def test_admin_create_list_detail_safe_dtos(self):
        # Real bootstrap/login session; member and anonymous denial covered in identity API tests.
        for path in ("/api/servers", self.path):
            response = await self.http.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(SYNTHETIC, response.text)
            self.assertNotIn('"credential_value"', response.text)
        item = (await self.http.get(self.path)).json()
        self.assertTrue(item["has_credential"])
        self.assertEqual(item["credential_type"], "bearer")
        self.assertEqual(item["observed_status"], "unknown")
        self.assertEqual(item["tools"], [])

    async def test_patch_preserves_replaces_and_clears_credential(self):
        response = await self.http.patch(self.path, json={"display_name": "Edited"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await self.db.repo.get(UUID(self.id))).credential.value, SYNTHETIC)
        response = await self.http.patch(self.path, json={"credential": {
            "kind": "header", "header_name": "X-Service-Key", "value": "synthetic-replacement-only"}})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("synthetic-replacement-only", response.text)
        self.assertEqual((await self.db.repo.get(UUID(self.id))).credential.kind, "header")
        response = await self.http.patch(self.path, json={"credential": None})
        self.assertFalse(response.json()["has_credential"])

    async def test_enable_disable_removal(self):
        self.assertFalse((await self.http.post(self.path + "/disable")).json()["enabled"])
        self.assertTrue((await self.http.post(self.path + "/enable")).json()["enabled"])
        self.assertEqual((await self.http.delete(self.path)).status_code, 204)
        self.assertEqual((await self.http.get(self.path)).status_code, 404)

    async def test_refresh_connected_then_failure_retains_stale_tools(self):
        success = (await self.http.post(self.path + "/refresh")).json()
        self.assertEqual(success["observed_status"], "connected")
        self.assertEqual(len(success["tools"]), 2)
        self.assertFalse(success["tools_stale"])
        self.fixture.mode = "dead"
        failed = (await self.http.post(self.path + "/refresh")).json()
        self.assertEqual(failed["observed_status"], "unreachable")
        self.assertTrue(failed["enabled"])
        self.assertTrue(failed["tools_stale"])
        self.assertEqual(failed["tools"], success["tools"])
        self.assertEqual(failed["failure_reason"], "UPSTREAM_UNAVAILABLE")

    async def test_disabled_refresh_never_contacts_upstream(self):
        await self.http.post(self.path + "/disable")
        self.assertEqual((await self.http.post(self.path + "/refresh")).status_code, 200)
        self.assertEqual(self.fixture.methods, [])

    async def test_duplicate_slug_conflict(self):
        response = await self.http.post("/api/servers", json={"slug": "server_a", "display_name": "Other",
                                                           "url": "http://localhost:9002/mcp"})
        self.assertEqual(response.status_code, 409)

    async def test_invalid_fields_and_secret_errors_are_sanitized(self):
        for body in ({"slug": "changed"}, {"enabled": "true"}, {"display_name": None}, {"url": None},
                     {"credential": {"kind": "header", "header_name": "Host", "value": SYNTHETIC}},
                     {"credential": {"kind": "bearer", "value": 42}}, {"unknown": SYNTHETIC}):
            response = await self.http.patch(self.path, json=body)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"error": "VALIDATION_ERROR"})
            self.assertNotIn(SYNTHETIC, response.text)

    async def test_invalid_uuid_and_missing_record(self):
        self.assertEqual((await self.http.get("/api/servers/invalid")).status_code, 422)
        self.assertEqual((await self.http.get("/api/servers/" + str(uuid4()))).status_code, 404)

    async def test_host_allowlist(self):
        response = await self.http.get("/api/servers", headers={"Host": "untrusted.invalid"})
        self.assertEqual(response.status_code, 400)

    async def test_malformed_json_does_not_echo_credential(self):
        response = await self.http.post("/api/servers", content='{"credential":"' + SYNTHETIC,
                                        headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(SYNTHETIC, response.text)

    async def test_repository_failure_has_safe_status(self):
        with patch.object(self.db.repo, "list", AsyncMock(side_effect=RepositoryUnavailable())):
            response = await self.http.get("/api/servers")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "REGISTRY_UNAVAILABLE"})

    async def test_invalid_url_and_credential_reflection_rejected(self):
        for url in ("http://user:password@localhost/mcp", "http://localhost/#fragment", "ftp://localhost/mcp"):
            self.assertEqual((await self.http.patch(self.path, json={"url": url})).status_code, 422)
        response = await self.http.patch(self.path, json={"display_name": SYNTHETIC})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(SYNTHETIC, response.text)

    async def test_persistent_repository_mcp_integration_and_disable(self):
        async with Client(streamable_http_client("http://127.0.0.1:8000/mcp", http_client=self.http), cache=None) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual([t.name for t in tools], ["server_a__echo", "server_a__shared_name"])
            result = await client.call_tool("server_a__echo", {"value": 5})
            self.assertEqual(result.structured_content, {"value": 5, "server": "server_a"})
            self.assertNotIn(SYNTHETIC, result.model_dump_json())
            await self.http.post(self.path + "/disable")
            self.assertEqual((await client.list_tools()).tools, [])
            self.assertTrue((await client.call_tool("server_a__echo", {"value": 1})).is_error)
            await self.http.post(self.path + "/enable")
            self.assertEqual(len((await client.list_tools()).tools), 2)

    async def test_stale_management_cache_never_becomes_live_mcp_catalog(self):
        await self.http.post(self.path + "/refresh")
        self.fixture.mode = "dead"
        async with Client(streamable_http_client("http://127.0.0.1:8000/mcp", http_client=self.http), cache=None) as client:
            self.assertEqual((await client.list_tools()).tools, [])
        view = (await self.http.get(self.path)).json()
        self.assertEqual(len(view["tools"]), 2)
        self.assertTrue(view["tools_stale"])
