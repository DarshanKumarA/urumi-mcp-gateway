"""Real official-client HTTP ASGI acceptance with persistent synthetic identities/audits."""
import asyncio
import io
import json
import logging
import unittest
from contextlib import AsyncExitStack, asynccontextmanager
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import httpx2
import sqlalchemy as sa
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

from urumi_gateway.api import create_app
from urumi_gateway.audit_repository import audit_events, AuditUnavailable
from urumi_gateway.identity import digest, token
from urumi_gateway.mcp_auth import MCPAuthentication, Principal
from urumi_gateway.models import Credential, Timeouts, Upstream
from urumi_gateway.upstream import UpstreamClient
from support import SYNTHETIC, SCHEMA, OUTPUT, UpstreamFixture
from test_identity import PASSWORD
from test_persistence import DatabaseFixture

ORIGIN = "http://127.0.0.1:8000"
ENDPOINT = ORIGIN + "/mcp"


class MCPAuditTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseFixture()
        self.a, self.b = UpstreamFixture("server_a"), UpstreamFixture("server_b")
        self.sa = Upstream("server_a", "A", "http://127.0.0.1:9001/mcp", credential=Credential("bearer", SYNTHETIC))
        self.sb = Upstream("server_b", "B", "http://127.0.0.1:9002/mcp")
        await self.db.repo.add(self.sa)
        await self.db.repo.add(self.sb)
        fixtures = {self.sa.id: self.a, self.sb.id: self.b}
        upstream = UpstreamClient(timeouts=Timeouts(1, .2), transport_factory=lambda s: fixtures[s.id].transport())
        self.app = create_app(self.db.repo, upstream=upstream)
        self.identity, self.audits = self.app.state.identity, self.app.state.audits
        self.user_a = await self.identity.bootstrap_admin("fixture_admin", PASSWORD)
        invite = await self.identity.invite(self.user_a, "fixture_member")
        self.user_b = await self.identity.accept(invite["token"], PASSWORD)
        self.key_a = await self.identity.create_key(self.user_a, "A fixture")
        self.key_b = await self.identity.create_key(self.user_b, "B fixture")
        self.started, self.stopped = asyncio.Event(), asyncio.Event()

        async def owner():
            async with AsyncExitStack() as stack:
                for app in (self.a.app, self.b.app, self.app):
                    await stack.enter_async_context(app.router.lifespan_context(app))
                self.http = await stack.enter_async_context(httpx2.AsyncClient(base_url=ORIGIN,
                    transport=httpx2.ASGITransport(app=self.app), headers={"Origin": ORIGIN}))
                self.started.set()
                await self.stopped.wait()
        self.owner = asyncio.create_task(owner())
        await asyncio.wait_for(self.started.wait(), 5)

    async def asyncTearDown(self):
        self.stopped.set()
        try:
            await self.owner
        finally:
            self.db.close()

    @asynccontextmanager
    async def connected(self, raw=None, mode="auto", statuses=None):
        async def response(response):
            if statuses is not None:
                statuses.append(response.status_code)
        headers = {"Authorization": "Bearer " + raw} if raw else {}
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=self.app), headers=headers,
                                     event_hooks={"response": [response]}) as http:
            async with Client(streamable_http_client(ENDPOINT, http_client=http), cache=None, mode=mode) as client:
                yield client

    async def rows(self):
        return (await self.audits.list_events(per_page=100))["items"]

    async def login(self, username="fixture_admin"):
        response = await self.http.post("/api/auth/login", json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 200)

    async def call(self, client, name="server_a__echo", value=7):
        return await client.session.call_tool(name, {"value": value})

    async def check_protocol(self, mode):
        async with self.connected(self.key_a["raw_key"], mode) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual([t.name for t in tools], ["server_a__echo", "server_a__shared_name", "server_b__add", "server_b__shared_name"])
            self.assertEqual(tools[0].input_schema, SCHEMA)
            self.assertEqual(tools[0].output_schema, OUTPUT)
            self.assertTrue(tools[0].annotations.read_only_hint)
            self.assertEqual(await self.rows(), [])  # Discovery is not a tool invocation.
            result = await self.call(client)
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content, {"server": "server_a", "value": 7})
        row = (await self.rows())[0]
        self.assertEqual(row["outcome"], "succeeded")
        self.assertEqual(row["user_id"], self.user_a["id"])
        self.assertEqual(row["api_key_id"], self.key_a["key"]["id"])

    async def test_current_protocol(self):
        await self.check_protocol("2026-07-28")

    async def test_legacy_protocol(self):
        await self.check_protocol("legacy")

    async def test_auto_protocol(self):
        await self.check_protocol("auto")

    async def test_official_client_missing_and_unknown_key(self):
        for raw in (None, token("key")):
            statuses = []
            with self.assertRaises(Exception):
                async with self.connected(raw, statuses=statuses):
                    self.fail("Unauthenticated MCP connection accepted")
            self.assertIn(401, statuses)
        self.assertEqual(self.a.methods + self.b.methods, [])
        self.assertEqual(await self.rows(), [])

    async def test_every_http_method_requires_bearer(self):
        for method in ("GET", "POST", "DELETE", "OPTIONS", "HEAD"):
            response = await self.http.request(method, "/mcp", content=b"{}")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], 'Bearer realm="urumi-gateway"')
        self.assertEqual(self.a.methods + self.b.methods, [])

    async def test_malformed_schemes_duplicate_headers_rejected(self):
        for value in ("Basic synthetic", "Bearer", "Bearer " + self.key_a["raw_key"] + " ",
                      "Bearer  " + self.key_a["raw_key"], "Bearer malformed"):
            self.assertEqual((await self.http.get("/mcp", headers={"Authorization": value})).status_code, 401)
        response = await self.http.get("/mcp", headers=[("Authorization", "Bearer " + self.key_a["raw_key"])] * 2)
        self.assertEqual(response.status_code, 401)

    async def test_query_cookie_arguments_and_forwarded_headers_cannot_authenticate(self):
        await self.login()
        for kwargs in ({"params": {"api_key": self.key_a["raw_key"]}},
                       {"headers": {"X-Api-Key": self.key_a["raw_key"], "X-User-Id": str(self.user_a["id"])}},
                       {"json": {"api_key": self.key_a["raw_key"]}}):
            self.assertEqual((await self.http.post("/mcp", **kwargs)).status_code, 401)
        self.assertEqual(self.a.methods + self.b.methods, [])

    async def test_revocation_next_existing_client_request_denied(self):
        statuses = []
        async with self.connected(self.key_b["raw_key"], statuses=statuses) as client:
            await client.list_tools()
            await self.call(client)
            await self.login()
            path = f'/api/users/{self.user_b["id"]}/keys/{self.key_b["key"]["id"]}'
            self.assertEqual((await self.http.delete(path)).status_code, 204)
            before = len(self.a.methods) + len(self.b.methods)
            with self.assertRaises(Exception):
                await client.list_tools(cache_mode="bypass")
            self.assertEqual(statuses[-1], 401)
            self.assertEqual(len(self.a.methods) + len(self.b.methods), before)
            self.assertEqual(len(await self.rows()), 1)

    async def test_disabled_user_next_request_denied(self):
        statuses = []
        async with self.connected(self.key_b["raw_key"], statuses=statuses) as client:
            await client.list_tools()
            await self.identity.repo.set_member_enabled(self.user_b["id"], False)
            before = len(self.a.methods) + len(self.b.methods)
            with self.assertRaises(Exception):
                await self.call(client)
            self.assertEqual(statuses[-1], 401)
            self.assertEqual(len(self.a.methods) + len(self.b.methods), before)
        self.assertEqual(await self.rows(), [])

    async def test_two_user_concurrent_attribution(self):
        barrier, arrivals, observed = asyncio.Event(), [], []
        original = self.app.state.invocations.invoke_tool
        async def overlap(principal, name, arguments):
            arrivals.append(principal.user_id)
            if len(arrivals) == 2:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), 2)
            observed.append((principal.user_id, principal.api_key_id, name))
            return await original(principal, name, arguments)
        async def user_call(issue, name):
            async with self.connected(issue["raw_key"]) as client:
                return await self.call(client, name)
        with patch.object(self.app.state.invocations, "invoke_tool", side_effect=overlap):
            results = await asyncio.gather(user_call(self.key_a, "server_a__echo"), user_call(self.key_b, "server_b__add"))
        self.assertTrue(all(not result.is_error for result in results))
        expected = {(self.user_a["id"], self.key_a["key"]["id"], "server_a__echo"),
                    (self.user_b["id"], self.key_b["key"]["id"], "server_b__add")}
        self.assertEqual(set(observed), expected)
        self.assertEqual({(r["user_id"], r["api_key_id"], r["gateway_tool"]) for r in await self.rows()}, expected)

    async def test_request_state_copy_and_authorization_removed(self):
        received = []
        async def downstream(scope, receive, send):
            received.append(scope)
        middleware = MCPAuthentication(downstream, identity=self.identity)
        original_state = {"fixture": True}
        scope = {"type": "http", "headers": [(b"authorization", ("Bearer " + self.key_a["raw_key"]).encode())],
                 "state": original_state}
        await middleware(scope, None, None)
        self.assertEqual(original_state, {"fixture": True})
        self.assertIsNot(received[0]["state"], original_state)
        self.assertEqual(received[0]["state"]["urumi_principal"].user_id, self.user_a["id"])
        self.assertEqual(received[0]["headers"], [])
        self.assertNotIn(self.key_a["raw_key"], repr(received[0]))

    async def test_start_is_committed_before_dispatch_and_exact_mapping(self):
        original = self.app.state.gateway.upstream.call
        async def check(server, name, arguments, **kwargs):
            # Separate connection can see the committed row before the tool call.
            with self.db.engine.connect() as c:
                row = c.execute(sa.select(audit_events)).mappings().one()
            self.assertEqual(row["outcome"], "started")
            self.assertEqual((row["server_id"], row["server_slug"], row["gateway_tool"], row["upstream_tool"]),
                             (self.sa.id, "server_a", "server_a__echo", "echo"))
            self.assertEqual(row["user_id"], self.user_a["id"])
            return await original(server, name, arguments, **kwargs)
        with patch.object(self.app.state.gateway.upstream, "call", side_effect=check):
            async with self.connected(self.key_a["raw_key"]) as client:
                self.assertFalse((await self.call(client)).is_error)
        row = (await self.rows())[0]
        self.assertGreaterEqual(row["duration_ms"], 0)
        self.assertIsNotNone(row["completed_at"])

    async def test_initial_audit_failure_prevents_any_upstream_operation(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            before = len(self.a.methods) + len(self.b.methods)
            with patch.object(self.audits, "start", AsyncMock(side_effect=AuditUnavailable())):
                result = await self.call(client)
            self.assertIn("AUDIT_UNAVAILABLE", result.content[0].text)
            self.assertEqual(len(self.a.methods) + len(self.b.methods), before)
            self.assertEqual(self.a.calls, [])
            self.assertEqual(await self.rows(), [])

    async def test_route_binding_failure_prevents_tool_dispatch(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            with patch.object(self.audits, "bind_tool", AsyncMock(side_effect=AuditUnavailable())):
                result = await self.call(client)
            self.assertIn("AUDIT_UNAVAILABLE", result.content[0].text)
        self.assertEqual(self.a.calls, [])
        self.assertEqual((await self.rows())[0]["outcome"], "failed")

    async def test_finalization_failure_one_call_started_record_unknown(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            with patch.object(self.audits, "finish", AsyncMock(side_effect=AuditUnavailable())):
                result = await self.call(client)
        self.assertEqual(len(self.a.calls), 1)
        self.assertIn("AUDIT_FINALIZATION_FAILED; write_outcome=unknown; retry_safe=false", result.content[0].text)
        row = (await self.rows())[0]
        self.assertEqual(row["outcome"], "started")
        self.assertIsNone(row["completed_at"])

    async def test_unknown_tool_audited_without_arbitrary_name(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            result = await client.session.call_tool(self.key_a["raw_key"], {})
        self.assertIn("UNKNOWN_TOOL", result.content[0].text)
        row = (await self.rows())[0]
        self.assertEqual(row["gateway_tool"], "<unresolved>")
        self.assertIsNone(row["server_id"])
        self.assertEqual(row["error_code"], "UNKNOWN_TOOL")
        self.assertNotIn(self.key_a["raw_key"], repr(row))

    async def test_validation_failure_audited(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            result = await client.session.call_tool("server_a__echo", {})
        self.assertIn("VALIDATION_ERROR", result.content[0].text)
        self.assertEqual((await self.rows())[0]["error_code"], "VALIDATION_ERROR")
        self.assertEqual((await self.rows())[0]["upstream_tool"], "echo")
        self.assertEqual(self.a.calls, [])

    async def test_dead_peer_audit_and_healthy_peer(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            await client.list_tools()
            self.a.mode = "dead"
            self.assertEqual([t.name for t in (await client.list_tools()).tools], ["server_b__add", "server_b__shared_name"])
            self.assertTrue((await self.call(client)).is_error)
            self.assertFalse((await self.call(client, "server_b__add")).is_error)
        rows = await self.rows()
        self.assertEqual({r["outcome"] for r in rows}, {"failed", "succeeded"})
        self.assertEqual(next(r for r in rows if r["server_slug"] == "server_a")["error_code"], "UPSTREAM_UNAVAILABLE")

    async def test_disabled_peer_disappears_call_audited_without_dispatch(self):
        async with self.connected(self.key_b["raw_key"]) as client:
            await client.list_tools()
            await self.db.repo.edit(self.sa.id, enabled=False)
            before = len(self.a.methods)
            self.assertEqual(len((await client.list_tools()).tools), 2)
            result = await self.call(client)
            self.assertIn("UPSTREAM_DISABLED", result.content[0].text)
            self.assertEqual(len(self.a.methods), before)
        row = (await self.rows())[0]
        self.assertEqual((row["user_id"], row["error_code"]), (self.user_b["id"], "UPSTREAM_DISABLED"))

    async def test_timeout_audited_once_and_peer_works(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            self.a.call_delay = 2
            result = await self.call(client)
            self.assertIn("UPSTREAM_TIMEOUT", result.content[0].text)
            self.assertFalse((await self.call(client, "server_b__add")).is_error)
        self.assertEqual(len(self.a.calls), 1)
        row = next(r for r in await self.rows() if r["server_slug"] == "server_a")
        self.assertEqual((row["outcome"], row["error_code"]), ("failed", "UPSTREAM_TIMEOUT"))

    async def test_malicious_upstream_error_sanitized(self):
        self.a.mode = "tool_error"
        async with self.connected(self.key_a["raw_key"]) as client:
            result = await self.call(client)
        row = (await self.rows())[0]
        self.assertEqual(row["error_code"], "UPSTREAM_TOOL_ERROR")
        self.assertNotIn(SYNTHETIC, repr(row) + result.model_dump_json())

    async def test_no_key_header_args_results_or_hashes_in_audit_or_logs(self):
        stream, handler = io.StringIO(), None
        handler = logging.StreamHandler(stream)
        logging.getLogger().addHandler(handler)
        try:
            async with self.connected(self.key_a["raw_key"]) as client:
                result = await self.call(client, value=8675309)
            serialized = json.dumps(await self.rows(), default=str)
            for forbidden in (self.key_a["raw_key"], digest(self.key_a["raw_key"]), SYNTHETIC,
                              "Authorization", "8675309", "arguments", "structured_content"):
                self.assertNotIn(forbidden, serialized + stream.getvalue())
            self.assertNotIn(self.key_a["raw_key"], str(self.a.headers + self.b.headers))
            self.assertNotIn(SYNTHETIC, result.model_dump_json())
            self.assertTrue(all(h.get("authorization") == "Bearer " + SYNTHETIC for h in self.a.headers))
        finally:
            logging.getLogger().removeHandler(handler)

    async def test_admin_audit_pagination_filters_and_member_denial(self):
        self.assertEqual((await self.http.get("/api/audits")).status_code, 401)
        async with self.connected(self.key_a["raw_key"]) as client:
            await self.call(client)
            await self.call(client, "server_b__add")
        await self.login("fixture_member")
        self.assertEqual((await self.http.get("/api/audits")).status_code, 403)
        await self.login()
        page = (await self.http.get("/api/audits", params={"per_page": 1})).json()
        self.assertEqual((page["total"], len(page["items"]), page["has_more"]), (2, 1, True))
        page = (await self.http.get("/api/audits", params={"user_id": str(self.user_a["id"]),
            "server_slug": "server_a", "tool": "server_a__echo", "outcome": "succeeded"})).json()
        self.assertEqual(page["total"], 1)
        self.assertNotIn("arguments", json.dumps(page))
        for query in ({"per_page": 101}, {"page": 0}, {"outcome": "arbitrary"}, {"unknown": "field"}, {"user_id": "invalid"}):
            self.assertEqual((await self.http.get("/api/audits", params=query)).status_code, 422)

    async def test_history_survives_registration_removal_and_key_revocation(self):
        async with self.connected(self.key_b["raw_key"]) as client:
            await self.call(client)
        before = (await self.rows())[0]
        await self.db.repo.remove(self.sa.id)
        await self.identity.revoke_key(self.user_a, self.user_b["id"], self.key_b["key"]["id"])
        await self.identity.repo.set_member_enabled(self.user_b["id"], False)
        self.db.engine.dispose()
        self.assertEqual((await self.rows())[0], before)

    async def test_audit_uuid_and_snapshots_immutable(self):
        async with self.connected(self.key_a["raw_key"]) as client:
            await self.call(client)
        for changes in ({"id": uuid4()}, {"server_slug": "changed"}, {"username": "changed"}, {"outcome": "started"}):
            with self.assertRaises(sa.exc.DBAPIError):
                with self.db.engine.begin() as c:
                    c.execute(audit_events.update().values(**changes))

    async def test_cancelled_invocation_leaves_started_without_replay(self):
        self.a.call_delay = 5
        principal = Principal(self.user_a["id"], self.user_a["username"], "admin", self.key_a["key"]["id"])
        task = asyncio.create_task(self.app.state.invocations.invoke_tool(principal, "server_a__echo", {"value": 1}))
        await asyncio.wait_for(self.a.call_started.wait(), 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(len(self.a.calls), 1)
        self.assertEqual((await self.rows())[0]["outcome"], "started")

    async def test_verifier_database_failure_fails_closed(self):
        with patch.object(self.identity, "verify_key", AsyncMock(side_effect=RuntimeError(SYNTHETIC))):
            response = await self.http.post("/mcp", headers={"Authorization": "Bearer " + self.key_a["raw_key"]})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "AUTH_UNAVAILABLE"})
        self.assertEqual(self.a.methods + self.b.methods, [])

    async def test_audit_list_database_failure_is_safe(self):
        await self.login()
        with patch.object(self.audits, "list_events", AsyncMock(side_effect=AuditUnavailable())):
            response = await self.http.get("/api/audits")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "AUDIT_UNAVAILABLE"})

    async def test_session_principal_reserved_shared_path_without_key(self):
        # Future chat must supply this from server-side session verification;
        # no HTTP caller can select a principal or auth source.
        principal = Principal(self.user_b["id"], self.user_b["username"], "member", None, "session")
        result = await self.app.state.invocations.invoke_tool(principal, "server_a__echo", {"value": 1})
        self.assertFalse(result.is_error)
        row = (await self.rows())[0]
        self.assertEqual(row["auth_source"], "session")
        self.assertIsNone(row["api_key_id"])
        self.assertEqual(row["user_id"], self.user_b["id"])

    async def test_replaced_registration_cannot_rebind_audit_to_another_server(self):
        start = self.audits.start
        async def replace(principal, target, now):
            event = await start(principal, target, now)
            await self.db.repo.remove(self.sa.id)
            replacement = Upstream("server_a", "Replacement", self.sa.url)
            await self.db.repo.add(replacement)
            # Avoid transport lookup of the replacement UUID; synthesize only
            # its discovery through the existing fixture.
            self.app.state.gateway.upstream.transport_factory = lambda s: self.a.transport()
            return event
        with patch.object(self.audits, "start", side_effect=replace):
            async with self.connected(self.key_a["raw_key"]) as client:
                result = await self.call(client)
        self.assertIn("UPSTREAM_CHANGED", result.content[0].text)
        self.assertEqual(self.a.calls, [])
        self.assertEqual((await self.rows())[0]["server_id"], self.sa.id)
