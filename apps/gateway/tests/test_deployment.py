"""Static packaging integration with migrated SQLite; real PG smoke is separate."""
import unittest
from unittest.mock import patch
import httpx2
import sqlalchemy as sa

from urumi_gateway.deployment import seed_builtins, database_ready, RECEIPTS
from urumi_gateway.database import bootstrap
from urumi_gateway.api import create_app
from test_persistence import DatabaseFixture

TOKEN = "SYNTHETIC-UPSTREAM-" + "x" * 40
URLS = {slug: "http://" + host + ".urumi.svc.cluster.local:8000/mcp" for slug, host in (
    ("woocommerce", "urumi-woo-mcp"), ("arithmetic", "urumi-arithmetic-mcp"),
    ("store_policy", "urumi-store-policy-mcp"))}


class DeploymentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseFixture()

    async def asyncTearDown(self):
        self.db.close()

    async def test_three_seeds_token_server_side_only(self):
        await seed_builtins(self.db.repo, TOKEN, URLS)
        rows = await self.db.repo.list()
        self.assertEqual({s.slug for s in rows}, set(URLS))
        for row in rows:
            if row.slug == "woocommerce":
                self.assertEqual(row.credential.value, TOKEN)
            else:
                self.assertIsNone(row.credential)
            self.assertNotIn(TOKEN, repr(row))

    async def test_repeat_seed_preserves_edits_and_deletion_and_token(self):
        await seed_builtins(self.db.repo, TOKEN, URLS)
        woo = await self.db.repo.get_by_slug("woocommerce")
        await self.db.repo.edit(woo.id, display_name="Managed", enabled=False, credential=None)
        arithmetic = await self.db.repo.get_by_slug("arithmetic")
        await self.db.repo.remove(arithmetic.id)
        await seed_builtins(self.db.repo, TOKEN, URLS)
        woo = await self.db.repo.get(woo.id)
        self.assertEqual(woo.display_name, "Managed")
        self.assertFalse(woo.enabled)
        self.assertIsNone(woo.credential)
        self.assertIsNone(await self.db.repo.get_by_slug("arithmetic"))

    async def test_no_ready_before_all_bootstrap_receipts(self):
        self.assertTrue(database_ready(self.db.engine, "schema"))
        self.assertFalse(database_ready(self.db.engine))
        await seed_builtins(self.db.repo, TOKEN, URLS)
        self.assertFalse(database_ready(self.db.engine))
        with self.db.engine.begin() as c:
            c.execute(bootstrap.insert().values(name="identity-admin-v1"))
        self.assertTrue(database_ready(self.db.engine))
        # Removal/disable is a valid managed state, not failed bootstrap.
        woo = await self.db.repo.get_by_slug("woocommerce")
        await self.db.repo.remove(woo.id)
        self.assertTrue(database_ready(self.db.engine))

    async def test_readiness_db_failure_safe_and_no_upstream_dependency(self):
        app = create_app(self.db.repo)
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1:8000") as http:
            with patch("urumi_gateway.deployment.database_ready", return_value=False):
                r = await http.get("/health/ready")
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json(), {"status": "not_ready"})
            with patch("urumi_gateway.deployment.database_ready", return_value=True), patch.object(
                    app.state.gateway, "list_tools", side_effect=AssertionError("Upstream probe forbidden")):
                self.assertEqual((await http.get("/health/ready")).status_code, 200)

    async def test_wrong_schema_not_ready(self):
        with self.db.engine.begin() as c:
            c.execute(sa.text("UPDATE alembic_version SET version_num='0002_identity'"))
        self.assertFalse(database_ready(self.db.engine, "schema"))

    async def test_invalid_service_token_is_not_seeded(self):
        with self.assertRaises(ValueError):
            await seed_builtins(self.db.repo, "short", URLS)
        self.assertEqual(await self.db.repo.list(), [])

    async def test_canonical_application_host_sdk_discovery(self):
        from mcp.client import Client
        from mcp.client.streamable_http import streamable_http_client
        from urumi_gateway.identity import AuthConfig
        from test_identity import PASSWORD
        origin = "http://gateway.urumi.test:8080"
        app = create_app(self.db.repo, auth_config=AuthConfig(origin=origin))
        user = await app.state.identity.bootstrap_admin("fixture_admin", PASSWORD)
        issued = await app.state.identity.create_key(user, "fixture")
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                    headers={"Authorization": "Bearer " + issued["raw_key"]}) as http:
                async with Client(streamable_http_client(origin + "/mcp", http_client=http)) as client:
                    self.assertEqual((await client.list_tools()).tools, [])
                self.assertEqual((await http.get(origin + "/mcp", headers={"Origin": origin})).status_code, 403)
