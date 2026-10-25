"""REST sessions/roles and token privacy, using real services and migrated SQL fixtures."""
import asyncio
import io
import logging
import unittest
from contextlib import AsyncExitStack
from datetime import timedelta
from uuid import UUID, uuid4

import httpx2
import sqlalchemy as sa

from urumi_gateway.api import create_app
from urumi_gateway.identity import AuthConfig, IdentityError
from urumi_gateway.identity_repository import sessions, api_keys
from test_identity import PASSWORD
from test_persistence import DatabaseFixture

ORIGIN = "http://127.0.0.1:8000"


class AuthApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseFixture()
        self.app = create_app(self.db.repo)
        self.service = self.app.state.identity
        self.admin = await self.service.bootstrap_admin("fixture_admin", PASSWORD)
        invite = await self.service.invite(self.admin, "fixture_member")
        self.member = await self.service.accept(invite["token"], PASSWORD)
        self.started, self.stopped = asyncio.Event(), asyncio.Event()

        async def owner():
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(self.app.router.lifespan_context(self.app))
                self.http = await stack.enter_async_context(httpx2.AsyncClient(
                    base_url=ORIGIN, transport=httpx2.ASGITransport(app=self.app), headers={"Origin": ORIGIN}))
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

    async def login(self, name="fixture_admin"):
        response = await self.http.post("/api/auth/login", json={"username": name, "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        return response

    async def issue_key(self):
        response = await self.http.post("/api/keys", json={"label": "fixture key"})
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def test_login_me_cookie_hash_only(self):
        response = await self.login()
        cookie = response.headers["set-cookie"]
        for expected in ("HttpOnly", "SameSite=lax", "Path=/", "Max-Age=28800"):
            self.assertIn(expected, cookie)
        self.assertNotIn("Secure", cookie)
        self.assertEqual(set(response.json()), {"id", "username", "role"})
        self.assertEqual((await self.http.get("/api/me")).json(), response.json())
        with self.db.engine.connect() as c:
            rows = list(c.execute(sa.select(sessions)).mappings())
        self.assertNotIn(self.http.cookies["urumi_session"], repr(rows))
        self.assertEqual(response.headers["cache-control"], "no-store")

    async def test_secure_cookie_and_production_config(self):
        self.service.config = AuthConfig(origin=ORIGIN, secure_cookie=True)
        response = await self.login()
        self.assertIn("Secure", response.headers["set-cookie"])

    async def test_invalid_login_generic(self):
        responses = []
        for name in ("unknown_user", "fixture_admin"):
            result = await self.http.post("/api/auth/login", json={"username": name, "password": "incorrect"})
            responses.append((result.status_code, result.json()))
            self.assertNotIn("set-cookie", result.headers)
        self.assertEqual(responses, [(401, {"error": "UNAUTHENTICATED"})] * 2)

    async def test_logout_revokes_and_clears(self):
        await self.login()
        raw = self.http.cookies["urumi_session"]
        response = await self.http.post("/api/auth/logout")
        self.assertEqual(response.status_code, 204)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertEqual((await self.http.get("/api/me")).status_code, 401)
        with self.assertRaises(IdentityError):
            await self.service.authenticate_session(raw)

    async def test_relogin_rotates_existing_session(self):
        await self.login()
        old = self.http.cookies["urumi_session"]
        await self.login()
        self.assertNotEqual(old, self.http.cookies["urumi_session"])
        with self.assertRaises(IdentityError):
            await self.service.authenticate_session(old)

    async def test_expired_session_api(self):
        await self.login()
        now = self.service.clock()
        self.service.clock = lambda: now + timedelta(days=1)
        self.assertEqual((await self.http.get("/api/me")).status_code, 401)

    async def test_disabled_member_session_api_and_enable(self):
        await self.login("fixture_member")
        await self.service.repo.set_member_enabled(self.member["id"], False)
        self.assertEqual((await self.http.get("/api/me")).status_code, 401)
        self.assertEqual((await self.http.post("/api/auth/login", json={
            "username": "fixture_member", "password": PASSWORD})).status_code, 401)
        await self.login()
        response = await self.http.post(f'/api/users/{self.member["id"]}/enable')
        self.assertTrue(response.json()["enabled"])
        self.assertEqual((await self.http.post(f'/api/users/{self.admin["id"]}/disable')).status_code, 404)

    async def test_anonymous_all_management_denied(self):
        for method, path in (("GET", "/api/servers"), ("POST", "/api/servers"),
                             ("GET", f"/api/servers/{uuid4()}"), ("PATCH", f"/api/servers/{uuid4()}"),
                             ("DELETE", f"/api/servers/{uuid4()}"),
                             *(("POST", f"/api/servers/{uuid4()}/{op}") for op in ("enable", "disable", "refresh"))):
            response = await self.http.request(method, path, json={})
            self.assertEqual(response.status_code, 401, path)

    async def test_member_all_management_denied(self):
        await self.login("fixture_member")
        for method, path in (("GET", "/api/servers"), ("POST", "/api/servers"),
                             ("GET", f"/api/servers/{uuid4()}"), ("PATCH", f"/api/servers/{uuid4()}"),
                             ("DELETE", f"/api/servers/{uuid4()}"),
                             *(("POST", f"/api/servers/{uuid4()}/{op}") for op in ("enable", "disable", "refresh"))):
            self.assertEqual((await self.http.request(method, path, json={})).status_code, 403, path)

    async def test_admin_management_allowed(self):
        await self.login()
        response = await self.http.post("/api/servers", json={"slug": "fixture", "display_name": "Fixture",
                                                               "url": "http://localhost:9001/mcp"})
        self.assertEqual(response.status_code, 201)
        path = "/api/servers/" + response.json()["id"]
        self.assertEqual((await self.http.get(path)).status_code, 200)
        self.assertEqual((await self.http.patch(path, json={"display_name": "Edited"})).status_code, 200)
        for op in ("disable", "enable"):
            self.assertEqual((await self.http.post(path + "/" + op)).status_code, 200)
        self.assertEqual((await self.http.delete(path)).status_code, 204)

    async def test_origin_missing_cross_origin_null_rejected(self):
        await self.login()
        for value in ("https://untrusted.invalid", "null", ORIGIN + "/", ""):
            self.assertEqual((await self.http.post("/api/keys", json={"label": "fixture"},
                headers={"Origin": value})).status_code, 403)
        del self.http.headers["Origin"]
        self.assertEqual((await self.http.post("/api/auth/logout")).status_code, 403)
        self.assertEqual((await self.http.get("/api/me")).status_code, 200)

    async def test_cross_site_fetch_rejected_even_with_origin(self):
        await self.login()
        for site in ("cross-site", "same-site"):
            self.assertEqual((await self.http.post("/api/keys", json={"label": "fixture"},
                headers={"Sec-Fetch-Site": site})).status_code, 403)

    async def test_login_csrf_rejected_no_cookie(self):
        response = await self.http.post("/api/auth/login", json={"username": "fixture_admin", "password": PASSWORD},
                                        headers={"Origin": "https://untrusted.invalid"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("set-cookie", response.headers)
        self.assertNotIn("access-control-allow-origin", response.headers)

    async def test_invite_admin_issue_once_safe_listing_accept(self):
        await self.login()
        issue = await self.http.post("/api/invitations", json={"username": "new_member"})
        self.assertEqual(issue.status_code, 201)
        raw = issue.json()["token"]
        listing = await self.http.get("/api/invitations")
        self.assertNotIn(raw, listing.text)
        self.assertNotIn("token_hash", listing.text)
        self.http.cookies.clear()
        accepted = await self.http.post("/api/invitations/accept", json={"token": raw, "password": PASSWORD})
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(accepted.json()["role"], "member")
        self.assertEqual((await self.http.post("/api/invitations/accept", json={"token": raw, "password": PASSWORD})).status_code, 400)

    async def test_member_invitation_and_user_management_denied(self):
        await self.login("fixture_member")
        for method, path, body in (("POST", "/api/invitations", {"username": "another_member"}),
                                   ("GET", "/api/invitations", {}), ("GET", "/api/users", {}),
                                   ("GET", f'/api/users/{self.admin["id"]}', {}),
                                   ("POST", f'/api/users/{self.admin["id"]}/disable', {})):
            self.assertEqual((await self.http.request(method, path, json=body)).status_code, 403)

    async def test_invite_no_role_or_username_override(self):
        await self.login()
        self.assertEqual((await self.http.post("/api/invitations", json={"username": "new_member", "role": "admin"})).status_code, 422)
        issue = (await self.http.post("/api/invitations", json={"username": "new_member"})).json()
        response = await self.http.post("/api/invitations/accept", json={"token": issue["token"],
            "password": PASSWORD, "username": "other_member"})
        self.assertEqual(response.status_code, 422)

    async def test_revoked_invite_api(self):
        await self.login()
        issue = (await self.http.post("/api/invitations", json={"username": "new_member"})).json()
        self.assertEqual((await self.http.delete('/api/invitations/' + issue['invitation']['id'])).status_code, 204)
        self.assertEqual((await self.http.post("/api/invitations/accept", json={"token": issue["token"], "password": PASSWORD})).status_code, 400)

    async def test_key_once_prefix_only_listing(self):
        await self.login("fixture_member")
        issue = await self.issue_key()
        response = await self.http.get("/api/keys")
        self.assertNotIn(issue["raw_key"], response.text)
        self.assertNotIn("hash", response.text)
        self.assertEqual(response.json()[0]["prefix"], issue["key"]["prefix"])
        with self.db.engine.connect() as c:
            self.assertNotIn(issue["raw_key"], repr(list(c.execute(sa.select(api_keys)).mappings())))

    async def test_own_key_revoke_api(self):
        await self.login("fixture_member")
        issue = await self.issue_key()
        self.assertEqual((await self.http.delete('/api/keys/' + issue['key']['id'])).status_code, 204)
        with self.assertRaises(IdentityError):
            await self.service.verify_key(issue["raw_key"])

    async def test_admin_identifies_and_revokes_member_key(self):
        await self.login("fixture_member")
        issue = await self.issue_key()
        await self.service.verify_key(issue["raw_key"])
        await self.login()
        users = (await self.http.get("/api/users")).json()
        self.assertIn("fixture_member", [user["username"] for user in users])
        keys_path = f'/api/users/{self.member["id"]}/keys'
        listing = await self.http.get(keys_path)
        self.assertNotIn(issue["raw_key"], listing.text)
        self.assertNotIn("hash", listing.text)
        self.assertEqual((await self.http.delete(keys_path + "/" + issue["key"]["id"])).status_code, 204)
        with self.assertRaises(IdentityError):
            await self.service.verify_key(issue["raw_key"])

    async def test_member_cannot_revoke_or_read_other_key(self):
        await self.login()
        issue = await self.issue_key()
        await self.login("fixture_member")
        self.assertEqual((await self.http.delete('/api/keys/' + issue['key']['id'])).status_code, 404)
        path = f'/api/users/{self.admin["id"]}/keys'
        self.assertEqual((await self.http.get(path)).status_code, 403)
        self.assertEqual((await self.http.delete(path + '/' + issue['key']['id'])).status_code, 403)
        await self.service.verify_key(issue["raw_key"])

    async def test_browser_identity_and_role_cannot_be_supplied(self):
        response = await self.http.get("/api/servers", headers={"X-User-Id": str(self.admin["id"]), "X-Role": "admin"})
        self.assertEqual(response.status_code, 401)
        await self.login("fixture_member")
        response = await self.http.post("/api/keys", json={"label": "fixture", "user_id": str(self.admin["id"])})
        self.assertEqual(response.status_code, 422)

    async def test_validation_and_logs_do_not_echo_sensitive_inputs(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        root = logging.getLogger()
        root.addHandler(handler)
        try:
            await self.login()
            issue = await self.issue_key()
            response = await self.http.post("/api/auth/login", json={"username": "fixture_admin",
                "password": PASSWORD, "unexpected": issue["raw_key"]})
            self.assertEqual(response.json(), {"error": "VALIDATION_ERROR"})
            self.assertNotIn(PASSWORD, response.text)
            self.assertNotIn(issue["raw_key"], response.text)
            for path in ("/api/me", "/api/users", "/api/keys", "/api/invitations"):
                response = await self.http.get(path)
                self.assertNotIn("hash", response.text)
                self.assertNotIn(PASSWORD, response.text)
                self.assertNotIn(issue["raw_key"], response.text)
            self.assertNotIn(PASSWORD, stream.getvalue())
            self.assertNotIn(issue["raw_key"], stream.getvalue())
        finally:
            root.removeHandler(handler)
