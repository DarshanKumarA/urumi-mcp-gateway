"""Synthetic identity fixtures; no real account, credential or cluster access."""
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

import sqlalchemy as sa

from urumi_gateway.identity import AuthConfig, IdentityError, IdentityService, Passwords, digest, token
from urumi_gateway.identity_repository import IdentityRepository, users, sessions, invitations, api_keys
from test_persistence import DatabaseFixture

PASSWORD = "synthetic-password-fixture-only"


class IdentityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseFixture()
        self.repo = IdentityRepository(self.db.engine)
        self.now = datetime.now(timezone.utc)
        self.service = IdentityService(self.repo, clock=lambda: self.now)
        self.admin = await self.service.bootstrap_admin("fixture_admin", PASSWORD)

    async def asyncTearDown(self):
        self.db.close()

    async def member(self, name="fixture_member"):
        issue = await self.service.invite(self.admin, name)
        return await self.service.accept(issue["token"], PASSWORD)

    def rows(self, table):
        with self.db.engine.connect() as c:
            return [dict(row) for row in c.execute(sa.select(table)).mappings()]

    async def test_argon2id_independent_salts_and_verification(self):
        first, second = await self.service.passwords.hash(PASSWORD), await self.service.passwords.hash(PASSWORD)
        self.assertTrue(first.startswith("$argon2id$v=19$m=65536,t=3,p=4$"))
        self.assertNotEqual(first, second)
        self.assertTrue(await self.service.passwords.verify(first, PASSWORD))
        self.assertFalse(await self.service.passwords.verify(first, "wrong"))

    async def test_password_limits(self):
        for value in ("short", "x" * 129, 123):
            with self.assertRaises(ValueError):
                await self.service.passwords.hash(value)

    async def test_bootstrap_idempotent_never_overwrites_password(self):
        before = self.rows(users)[0]["password_hash"]
        again = await self.service.bootstrap_admin("fixture_admin", "synthetic-other-password")
        self.assertEqual(again["id"], self.admin["id"])
        self.assertEqual(self.rows(users)[0]["password_hash"], before)
        await self.service.login("fixture_admin", PASSWORD)

    async def test_bootstrap_other_identity_conflict(self):
        with self.assertRaisesRegex(ValueError, "BOOTSTRAP_CONFLICT"):
            await self.service.bootstrap_admin("other_admin", PASSWORD)
        member = await self.member()
        with self.assertRaisesRegex(ValueError, "BOOTSTRAP_CONFLICT"):
            await self.service.bootstrap_admin(member["username"], PASSWORD)

    async def test_username_unique_and_immutable_in_database(self):
        with self.db.engine.connect() as c:
            row = dict(c.execute(sa.select(users)).mappings().one())
        row["id"] = uuid4()
        with self.assertRaises(sa.exc.IntegrityError):
            with self.db.engine.begin() as c:
                c.execute(users.insert().values(**row))
        for changes in ({"username": "changed_name"}, {"id": uuid4()}):
            with self.assertRaises(sa.exc.DBAPIError):
                with self.db.engine.begin() as c:
                    c.execute(users.update().values(**changes))

    async def test_generic_login_failure_verifies_dummy(self):
        for name, secret in (("absent_user", PASSWORD), ("fixture_admin", "wrong")):
            with patch.object(self.service.passwords, "verify", wraps=self.service.passwords.verify) as verify:
                with self.assertRaisesRegex(IdentityError, "^UNAUTHENTICATED$"):
                    await self.service.login(name, secret)
                self.assertEqual(verify.await_count, 1)

    async def test_session_hash_only_and_safe_identity(self):
        user, raw = await self.service.login("fixture_admin", PASSWORD)
        rows = self.rows(sessions)
        self.assertEqual(rows[0]["token_hash"], digest(raw))
        self.assertNotIn(raw, repr(rows))
        identity = await self.service.authenticate_session(raw)
        self.assertEqual(identity[0]["id"], user["id"])
        self.assertNotIn("password_hash", repr(identity))

    async def test_session_expired(self):
        _, raw = await self.service.login("fixture_admin", PASSWORD)
        self.now += timedelta(seconds=self.service.config.session_seconds)
        with self.assertRaises(IdentityError):
            await self.service.authenticate_session(raw)

    async def test_session_revoked(self):
        _, raw = await self.service.login("fixture_admin", PASSWORD)
        _, sid = await self.service.authenticate_session(raw)
        await self.service.logout(sid)
        with self.assertRaises(IdentityError):
            await self.service.authenticate_session(raw)

    async def test_disabled_user_rejects_login_session_and_key(self):
        member = await self.member()
        _, raw = await self.service.login(member["username"], PASSWORD)
        key = await self.service.create_key(member, "fixture")
        await self.repo.set_member_enabled(member["id"], False)
        for operation in (self.service.login(member["username"], PASSWORD),
                          self.service.authenticate_session(raw), self.service.verify_key(key["raw_key"])):
            with self.assertRaises(IdentityError):
                await operation

    async def test_malformed_or_unknown_session(self):
        for raw in (None, "wrong", token("session")):
            with self.assertRaises(IdentityError):
                await self.service.authenticate_session(raw)

    async def test_invitation_single_use_hash_only_member_identity(self):
        issue = await self.service.invite(self.admin, "invited_member")
        self.assertNotIn(issue["token"], repr(self.rows(invitations)))
        self.assertEqual(self.rows(invitations)[0]["token_hash"], digest(issue["token"]))
        member = await self.service.accept(issue["token"], PASSWORD)
        self.assertEqual((member["username"], member["role"]), ("invited_member", "member"))
        with self.assertRaisesRegex(IdentityError, "INVITATION_INVALID"):
            await self.service.accept(issue["token"], PASSWORD)

    async def test_invitation_concurrent_accept_only_one(self):
        issue = await self.service.invite(self.admin, "concurrent_member")
        results = await asyncio.gather(*(self.service.accept(issue["token"], PASSWORD) for _ in range(2)),
                                       return_exceptions=True)
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(sum(isinstance(result, IdentityError) for result in results), 1)

    async def test_invitation_expired_revoked_invalid(self):
        expired = await self.service.invite(self.admin, "expired_member")
        revoked = await self.service.invite(self.admin, "revoked_member")
        await self.repo.revoke_invitation(revoked["invitation"]["id"], self.now)
        self.now += timedelta(days=2)
        for raw in (expired["token"], revoked["token"], token("invite"), "wrong"):
            with self.assertRaises(IdentityError):
                await self.service.accept(raw, PASSWORD)

    async def test_member_cannot_invite(self):
        member = await self.member()
        with self.assertRaisesRegex(IdentityError, "FORBIDDEN"):
            await self.service.invite(member, "another_member")

    async def test_invitation_cannot_target_existing_user(self):
        with self.assertRaises(ValueError):
            await self.service.invite(self.admin, "fixture_admin")

    async def test_invitation_database_forbids_admin_role(self):
        await self.service.invite(self.admin, "invited_member")
        with self.assertRaises(sa.exc.IntegrityError):
            with self.db.engine.begin() as c:
                c.execute(invitations.update().values(role="admin"))

    async def test_key_hash_prefix_safe_metadata_verifier(self):
        issue = await self.service.create_key(self.admin, " fixture key ")
        raw, record = issue["raw_key"], issue["key"]
        self.assertTrue(raw.startswith("urumi_key_"))
        self.assertTrue(raw.startswith(record["prefix"]))
        self.assertLess(len(record["prefix"]), len(raw))
        self.assertEqual(self.rows(api_keys)[0]["key_hash"], digest(raw))
        self.assertNotIn(raw, repr(self.rows(api_keys)))
        metadata = await self.repo.list_keys(self.admin["id"])
        self.assertNotIn("key_hash", repr(metadata))
        self.assertNotIn(raw, repr(metadata))
        identity = await self.service.verify_key(raw)
        self.assertEqual(identity["key_id"], record["id"])
        self.assertNotIn("hash", repr(identity))

    async def test_key_unknown_malformed(self):
        for raw in (None, "", "urumi_", token("key"), "x" * 4096):
            with self.assertRaises(IdentityError):
                await self.service.verify_key(raw)

    async def test_own_key_revocation_immediate(self):
        issue = await self.service.create_key(self.admin, "fixture")
        await self.service.revoke_key(self.admin, self.admin["id"], issue["key"]["id"])
        with self.assertRaises(IdentityError):
            await self.service.verify_key(issue["raw_key"])

    async def test_admin_revokes_member_key_immediately(self):
        member = await self.member()
        issue = await self.service.create_key(member, "fixture")
        await self.service.verify_key(issue["raw_key"])
        await self.service.revoke_key(self.admin, member["id"], issue["key"]["id"])
        with self.assertRaises(IdentityError):
            await self.service.verify_key(issue["raw_key"])

    async def test_member_cannot_revoke_other_key(self):
        member = await self.member()
        issue = await self.service.create_key(self.admin, "fixture")
        with self.assertRaisesRegex(IdentityError, "FORBIDDEN"):
            await self.service.revoke_key(member, self.admin["id"], issue["key"]["id"])
        with self.assertRaises(KeyError):
            await self.service.revoke_key(member, member["id"], issue["key"]["id"])
        await self.service.verify_key(issue["raw_key"])

    async def test_reconnect_persistence(self):
        _, raw = await self.service.login("fixture_admin", PASSWORD)
        issue = await self.service.create_key(self.admin, "fixture")
        self.db.engine.dispose()
        fresh = IdentityService(IdentityRepository(self.db.engine))
        await fresh.authenticate_session(raw)
        await fresh.verify_key(issue["raw_key"])

    async def test_configuration_fails_closed(self):
        for kwargs in ({"production": True}, {"origin": "http://localhost/path"},
                       {"origin": "http://user:pass@localhost"}, {"session_seconds": 0},
                       {"session_seconds": True}, {"invitation_seconds": 9999999}):
            with self.assertRaises(ValueError):
                AuthConfig(**kwargs)
        self.assertTrue(AuthConfig(origin="https://gateway.urumi.test", production=True, secure_cookie=True).secure_cookie)

    async def test_identity_migration_is_explicit_not_startup_ddl(self):
        from urumi_gateway.api import create_app
        from test_persistence import migrate
        migrate(self.db.engine, "0001_registry", down=True)
        before = sa.inspect(self.db.engine).get_table_names()
        app = create_app(self.db.repo)
        async with app.router.lifespan_context(app):
            self.assertEqual(sa.inspect(self.db.engine).get_table_names(), before)
        self.assertNotIn("users", before)
        migrate(self.db.engine)
        service = IdentityService(IdentityRepository(self.db.engine))
        await service.bootstrap_admin("fresh_admin", PASSWORD)

    async def test_bootstrap_command_missing_files_fails_without_details(self):
        import contextlib
        import io
        import os
        from urumi_gateway.bootstrap_admin import bootstrap
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output):
            self.assertEqual(await bootstrap(), 1)
        self.assertEqual(output.getvalue().strip(), "BOOTSTRAP_ADMIN_FAILED; no credential details emitted.")

    async def test_bootstrap_command_uses_file_and_preserves_existing_admin(self):
        import contextlib
        import io
        import os
        from pathlib import Path
        from urumi_gateway.bootstrap_admin import bootstrap
        directory = Path(self.db.directory.name)
        (directory / "password.txt").write_text(PASSWORD, encoding="utf-8")
        (directory / "url.txt").write_text("synthetic-fixture-url", encoding="utf-8")
        output = io.StringIO()
        before = self.rows(users)[0]["password_hash"]
        with patch.dict(os.environ, {"URUMI_DATABASE_URL_FILE": str(directory / "url.txt"),
                "URUMI_BOOTSTRAP_PASSWORD_FILE": str(directory / "password.txt"),
                "URUMI_BOOTSTRAP_USERNAME": "fixture_admin"}), \
                patch("urumi_gateway.bootstrap_admin.make_engine", return_value=self.db.engine), \
                contextlib.redirect_stdout(output):
            self.assertEqual(await bootstrap(), 0)
        self.assertNotIn(PASSWORD, output.getvalue())
        self.assertEqual(self.rows(users)[0]["password_hash"], before)
