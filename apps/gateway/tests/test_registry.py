import dataclasses
import hashlib
import unittest
from uuid import uuid4

from urumi_gateway.core import exposed_name
from urumi_gateway.models import Credential, Observation, Timeouts, Upstream
from urumi_gateway.repository import MemoryRepository
from support import SYNTHETIC


class RegistryTests(unittest.IsolatedAsyncioTestCase):
    def server(self, **kwargs):
        return Upstream(**{"slug": "server_a", "display_name": "A", "url": "http://localhost:8001/mcp", **kwargs})

    async def test_registration_defaults(self):
        server = self.server()
        repo = MemoryRepository()
        await repo.add(server)
        self.assertEqual(server.configured_state, "enabled")
        self.assertEqual((await repo.health(server.id)).health, "unknown")

    async def test_identity_and_slug_immutable(self):
        server = self.server()
        repo = MemoryRepository()
        await repo.add(server)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            server.slug = "different"
        for field, value in (("slug", "other"), ("id", uuid4()), ("revision", 10), ("extra", "bad")):
            with self.assertRaises(ValueError):
                await repo.edit(server.id, **{field: value})

    async def test_unique_identity_and_slug(self):
        repo = MemoryRepository()
        first = self.server()
        await repo.add(first)
        for server in (first, self.server(), self.server(slug="other", id=first.id)):
            with self.assertRaises(ValueError):
                await repo.add(server)

    async def test_edit_enable_disable_remove(self):
        repo = MemoryRepository()
        server = self.server()
        await repo.add(server)
        edited = await repo.edit(server.id, enabled=False, display_name="Edited", url="https://localhost/mcp")
        self.assertEqual(edited.configured_state, "disabled")
        self.assertEqual(edited.id, server.id)
        self.assertEqual(edited.slug, server.slug)
        self.assertTrue((await repo.edit(server.id, enabled=True)).enabled)
        await repo.remove(server.id)
        self.assertIsNone(await repo.get(server.id))

    async def test_health_never_changes_enabled_and_old_observation_ignored(self):
        repo = MemoryRepository()
        server = self.server()
        await repo.add(server)
        await repo.observe(server, Observation("unreachable", "UPSTREAM_TIMEOUT"))
        self.assertTrue((await repo.get(server.id)).enabled)
        await repo.edit(server.id, enabled=False)
        self.assertFalse(await repo.observe(server, Observation("connected")))
        self.assertEqual((await repo.health(server.id)).health, "unknown")

    def test_slug_validation(self):
        for slug in ("", "UPPER", "a__b", "a-b", "a.b", "a/", "a" * 33, "_a", "a_"):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                self.server(slug=slug)
        self.server(slug="server_2")

    def test_url_validation_and_safe_error(self):
        for url in ("file:///tmp/mcp", "http://user:password@localhost/mcp", "http://localhost/mcp?token=x",
                    "http://localhost/#fragment", "http://localhost:bad/mcp", "no-host"):
            with self.assertRaisesRegex(ValueError, "^INVALID_UPSTREAM_URL$"):
                self.server(url=url)

    def test_credentials_and_public_projection(self):
        for credential in (Credential("bearer", SYNTHETIC), Credential("header", SYNTHETIC, "X-Service-Key")):
            server = self.server(credential=credential)
            self.assertNotIn(SYNTHETIC, repr(server) + repr(credential) + str(server.public_info()))
            self.assertTrue(server.public_info()["has_credential"])
            self.assertTrue(any(SYNTHETIC in value for value in credential.headers().values()))

    def test_header_injection_and_reserved_headers_rejected(self):
        for header in ("Host", "Origin", "Content-Type", "Mcp-Param-Key", "Proxy-Authorization", "bad\r\nname"):
            with self.assertRaises(ValueError):
                Credential("header", SYNTHETIC, header)
        for value in ("", "bad\nvalue", "bad\rvalue"):
            with self.assertRaises(ValueError):
                Credential("bearer", value)

    def test_namespacing_and_length_suffix(self):
        self.assertEqual(exposed_name("server_a", "shared_name"), "server_a__shared_name")
        self.assertEqual(exposed_name("server_a", "part__tool"), "server_a__part__tool")
        long_name = exposed_name("server_a", "a" * 128)
        self.assertEqual(len(long_name), 128)
        self.assertEqual(long_name, exposed_name("server_a", "a" * 128))
        self.assertNotEqual(long_name, exposed_name("server_b", "a" * 128))

    def test_timeout_configuration(self):
        self.assertEqual(Timeouts().discovery, 5)
        self.assertEqual(Timeouts().call, 30)
        for value in (0, -1, float("nan"), float("inf"), True, 121):
            with self.assertRaises(ValueError):
                Timeouts(discovery=value)

    def test_exactly_128_character_name_unchanged(self):
        original = "x" * 118
        full = "server_a__" + original
        self.assertEqual(len(full), 128)
        self.assertEqual(exposed_name("server_a", original), full)

    def test_overlong_name_uses_complete_content_digest_and_safe_characters(self):
        original = "Ab_9.-" * 21
        full = "server_a__" + original
        result = exposed_name("server_a", original)
        self.assertEqual(len(result), 128)
        self.assertRegex(result, r"^[A-Za-z0-9_.-]{1,128}$")
        self.assertEqual(result, full[:111] + "_" + hashlib.sha256(full.encode()).hexdigest()[:16])
        self.assertEqual(result, exposed_name("server_a", original))

    def test_equal_length_long_common_prefix_names_remain_distinct(self):
        first, second = "x" * 127 + "a", "x" * 127 + "b"
        self.assertEqual(len(first), len(second))
        self.assertEqual(first[:127], second[:127])
        self.assertNotEqual(exposed_name("server_a", first), exposed_name("server_a", second))

    def test_long_names_from_distinct_slugs_remain_distinct(self):
        original = "x" * 128
        first = exposed_name("server_a", original)
        second = exposed_name("server_b", original)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first[-16:], second[-16:])
