"""SQLite fast tests of the SQL repository; PostgreSQL has a separate real smoke."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from urumi_gateway.database import SQLRepository, metadata, servers, make_engine
from urumi_gateway.models import Credential, Observation, Upstream
from support import SYNTHETIC


def migrate(engine, revision="head", *, down=False):
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        (command.downgrade if down else command.upgrade)(cfg, revision)


class DatabaseFixture:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urumi-registry-test-")
        self.url = sa.URL.create("sqlite", database=str(Path(self.directory.name) / "registry.db"))
        self.engine = sa.create_engine(self.url, hide_parameters=True)
        migrate(self.engine)
        self.repo = SQLRepository(self.engine)

    def close(self):
        self.engine.dispose()
        self.directory.cleanup()


class PersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseFixture()
        self.repo = self.db.repo
        self.server = Upstream("example", "Example", "http://localhost:9001/mcp",
                               credential=Credential("bearer", SYNTHETIC))
        await self.repo.add(self.server)

    async def asyncTearDown(self):
        self.db.close()

    async def test_crud_survives_new_repository_and_engine(self):
        self.db.engine.dispose()
        engine = sa.create_engine(self.db.url, hide_parameters=True)
        try:
            repo = SQLRepository(engine)
            self.assertEqual(await repo.get(self.server.id), self.server)
            self.assertEqual((await repo.get_by_slug("example")).id, self.server.id)
            self.assertEqual(len(await repo.list()), 1)
            updated = await repo.edit(self.server.id, display_name="Edited", enabled=False)
            self.assertFalse((await self.repo.get(self.server.id)).enabled)
            self.assertEqual(updated.revision, 1)
            self.assertEqual(updated.created_at, self.server.created_at)
            self.assertGreaterEqual(updated.updated_at, updated.created_at)
            self.assertTrue((await repo.edit(self.server.id, enabled=True)).enabled)
        finally:
            engine.dispose()

    async def test_unique_slug_application_and_database(self):
        with self.assertRaises(ValueError):
            await self.repo.add(Upstream("example", "Other", "http://localhost/mcp"))
        with self.assertRaises(sa.exc.IntegrityError):
            with self.db.engine.begin() as c:
                row = dict(c.execute(sa.select(servers)).mappings().one())
                row["id"] = uuid4()
                c.execute(servers.insert().values(**row))

    async def test_identity_immutable_application_and_database(self):
        for changes in ({"slug": "changed"}, {"id": uuid4()}, {"revision": 4}):
            with self.assertRaises(ValueError):
                await self.repo.edit(self.server.id, **changes)
        for changes in ({"slug": "changed"}, {"id": uuid4()}):
            with self.assertRaises(sa.exc.IntegrityError):
                with self.db.engine.begin() as c:
                    c.execute(servers.update().values(**changes))

    async def test_database_rejects_inconsistent_credential_columns(self):
        with self.assertRaises(sa.exc.IntegrityError):
            with self.db.engine.begin() as c:
                c.execute(servers.update().values(credential_type=None, credential_value=SYNTHETIC))

    async def test_credential_preserve_replace_clear(self):
        changed = await self.repo.edit(self.server.id, display_name="Edited")
        self.assertEqual(changed.credential.value, SYNTHETIC)
        other = Credential("header", "synthetic-replacement-only", "X-Upstream-Key")
        await self.repo.edit(self.server.id, credential=other)
        self.assertEqual((await self.repo.get(self.server.id)).credential, other)
        await self.repo.edit(self.server.id, credential=None)
        self.assertIsNone((await self.repo.get(self.server.id)).credential)

    async def test_status_and_last_good_metadata_persist(self):
        tool = {"name": "example__echo", "inputSchema": {"type": "object"}}
        self.assertTrue(await self.repo.observe(self.server, Observation("connected"), tools=[tool]))
        repo = SQLRepository(self.db.engine)
        self.assertEqual((await repo.cached_tools(self.server.id))["items"], [tool])
        self.assertIsNotNone((await repo.health(self.server.id)).checked_at)
        await repo.observe(self.server, Observation("unreachable", "UPSTREAM_TIMEOUT"))
        self.assertEqual((await repo.cached_tools(self.server.id))["items"], [tool])
        self.assertEqual((await repo.health(self.server.id)).error_code, "UPSTREAM_TIMEOUT")
        self.assertTrue((await repo.get(self.server.id)).enabled)

    async def test_edit_invalidates_cache_and_late_observation(self):
        await self.repo.observe(self.server, Observation("connected"), tools=[{"name": "old"}])
        await self.repo.edit(self.server.id, enabled=False)
        self.assertFalse(await self.repo.observe(self.server, Observation("connected"), tools=[{"name": "late"}]))
        self.assertEqual((await self.repo.cached_tools(self.server.id))["items"], [])
        self.assertEqual((await self.repo.health(self.server.id)).health, "unknown")

    async def test_removal_cleans_secret_cache_health(self):
        await self.repo.observe(self.server, Observation("connected"), tools=[{"name": "old"}])
        await self.repo.remove(self.server.id)
        self.assertIsNone(await self.repo.get(self.server.id))
        self.assertIsNone(await self.repo.get_by_slug(self.server.slug))
        self.assertFalse(await self.repo.observe(self.server, Observation("connected")))
        self.assertEqual((await self.repo.cached_tools(self.server.id))["items"], [])

    async def test_seed_idempotent_no_overwrite_no_resurrection(self):
        await self.repo.seed_woocommerce()
        original = await self.repo.get_by_slug("woocommerce")
        self.assertEqual(original.display_name, "WooCommerce")
        self.assertIsNone(original.credential)
        await self.repo.edit(original.id, display_name="Admin choice", enabled=False,
                             url="http://localhost:9002/mcp", credential=Credential("bearer", SYNTHETIC))
        await self.repo.seed_woocommerce()
        current = await self.repo.get(original.id)
        self.assertEqual(current.display_name, "Admin choice")
        self.assertFalse(current.enabled)
        self.assertEqual(current.credential.value, SYNTHETIC)
        await self.repo.remove(original.id)
        await self.repo.seed_woocommerce()
        self.assertIsNone(await self.repo.get(original.id))

    async def test_seed_preserves_preexisting_registration(self):
        original = Upstream("woocommerce", "Preexisting", "http://localhost:9003/mcp", enabled=False)
        await self.repo.add(original)
        await self.repo.seed_woocommerce()
        self.assertEqual(await self.repo.get_by_slug("woocommerce"), original)

    async def test_concurrent_seed_one_registration(self):
        await asyncio.gather(self.repo.seed_woocommerce(), self.repo.seed_woocommerce())
        self.assertEqual(len([s for s in await self.repo.list() if s.slug == "woocommerce"]), 1)

    async def test_migration_schema_matches_and_reversible_on_fixture(self):
        with self.db.engine.connect() as c:
            self.assertEqual(compare_metadata(MigrationContext.configure(c), metadata), [])
        migrate(self.db.engine, "base", down=True)
        self.assertNotIn("mcp_servers", sa.inspect(self.db.engine).get_table_names())
        migrate(self.db.engine)
        self.assertEqual(await self.repo.list(), [])

    def test_production_engine_rejects_sqlite(self):
        with self.assertRaisesRegex(ValueError, "POSTGRESQL_REQUIRED"):
            make_engine("sqlite://")

    def test_url_validation_and_normalization(self):
        for url in ("http://@localhost/mcp", "http://localhost:0/mcp", "http://localhost:99999/mcp",
                    "http://localhost/#x", "http://localhost/?credential=x", "file:///mcp",
                    "http://localhost/" + "x" * 2048, "http://localhost/#", "http://localhost/?",
                    "http://localhost/\x7f", b"http://localhost/mcp"):
            with self.subTest(url=url[:60]), self.assertRaises(ValueError):
                Upstream("example", "Example", url)
        self.assertEqual(Upstream("a", "A", "HTTP://LOCALHOST:80/mcp").url, "http://localhost/mcp")

    def test_observation_cannot_store_raw_error_text(self):
        with self.assertRaises(ValueError):
            Observation("unreachable", SYNTHETIC)
