"""Opt-in real PostgreSQL smoke. Only an EMPTY loopback disposable fixture DB.

Reads URUMI_TEST_DATABASE_URL_FILE; never prints the URL, values or raw DB errors.
Does not start Docker/Kubernetes. Caller owns the disposable DB lifecycle.
"""
import asyncio
import os
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from urumi_gateway.database import SQLRepository, make_engine, metadata, servers
from urumi_gateway.models import Credential, Observation, Upstream
from test_persistence import migrate
from support import SYNTHETIC
from urumi_gateway.identity import IdentityService, IdentityError, digest
from urumi_gateway.identity_repository import IdentityRepository, users, sessions, invitations, api_keys


async def exercise(engine):
    repo = SQLRepository(engine)
    await asyncio.gather(repo.seed_woocommerce(), repo.seed_woocommerce())
    woo = await repo.get_by_slug("woocommerce")
    assert woo and woo.credential is None
    await repo.edit(woo.id, enabled=False, display_name="Managed choice")
    await repo.seed_woocommerce()
    assert (await repo.get(woo.id)).display_name == "Managed choice"
    item = Upstream("fixture", "Fixture", "http://localhost:9001/mcp", credential=Credential("bearer", SYNTHETIC))
    await repo.add(item)
    try:
        await repo.add(Upstream("fixture", "Duplicate", "http://localhost/mcp"))
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate accepted")
    # Force direct DB uniqueness and immutability checks, not merely application checks.
    try:
        with engine.begin() as c:
            row = dict(c.execute(sa.select(servers).where(servers.c.id == item.id)).mappings().one())
            row["id"] = uuid4()
            c.execute(servers.insert().values(**row))
    except sa.exc.IntegrityError:
        pass
    else:
        raise AssertionError("Database duplicate slug accepted")
    for change in ({"slug": "changed"}, {"id": woo.id}):
        try:
            with engine.begin() as c:
                c.execute(servers.update().where(servers.c.id == item.id).values(**change))
        except sa.exc.DBAPIError:
            pass
        else:
            raise AssertionError("Immutable identity changed")
    try:
        with engine.begin() as c:
            c.execute(servers.update().where(servers.c.id == item.id).values(credential_type=None))
    except sa.exc.IntegrityError:
        pass
    else:
        raise AssertionError("Inconsistent credential columns accepted")
    with engine.connect() as c:
        assert compare_metadata(MigrationContext.configure(c), metadata) == []
    await repo.observe(item, Observation("connected"), tools=[{"name": "fixture__echo", "inputSchema": {"type": "object"}}])
    await repo.observe(item, Observation("unreachable", "UPSTREAM_TIMEOUT"))
    engine.dispose()  # New connections, same persisted PostgreSQL data.
    second = SQLRepository(engine)
    assert (await second.get(item.id)).credential.value == SYNTHETIC
    assert (await second.health(item.id)).error_code == "UPSTREAM_TIMEOUT"
    assert len((await second.cached_tools(item.id))["items"]) == 1
    edited = await second.edit(item.id, enabled=False)
    assert edited.credential.value == SYNTHETIC
    assert not await repo.observe(item, Observation("connected"))
    await second.edit(item.id, credential=Credential("header", SYNTHETIC, "X-Fixture"))
    assert (await repo.get(item.id)).credential.kind == "header"
    await second.edit(item.id, enabled=True, credential=None)
    assert (await repo.get(item.id)).credential is None
    await second.remove(item.id)
    assert await repo.get(item.id) is None
    assert (await repo.cached_tools(item.id))["items"] == []
    await repo.remove(woo.id)
    await repo.seed_woocommerce()
    assert await repo.get_by_slug("woocommerce") is None


async def identity_exercise(engine):
    service = IdentityService(IdentityRepository(engine))
    synthetic_password = "synthetic-postgres-fixture-only"
    # Concurrent same-identity bootstrap must converge, never reset a password.
    admins = await asyncio.gather(*(service.bootstrap_admin("fixture_admin", synthetic_password) for _ in range(2)))
    assert admins[0]["id"] == admins[1]["id"]
    admin = admins[0]
    with engine.connect() as c:
        before_hash = c.execute(sa.select(users.c.password_hash)).scalar_one()
    assert before_hash.startswith("$argon2id$") and synthetic_password not in before_hash
    await service.bootstrap_admin("fixture_admin", "synthetic-unused-replacement")
    with engine.connect() as c:
        assert c.execute(sa.select(users.c.password_hash)).scalar_one() == before_hash
    _, session_token = await service.login("fixture_admin", synthetic_password)
    invitation = await service.invite(admin, "fixture_member")
    results = await asyncio.gather(*(service.accept(invitation["token"], synthetic_password) for _ in range(2)),
                                   return_exceptions=True)
    assert sum(isinstance(result, dict) for result in results) == 1
    assert sum(isinstance(result, IdentityError) for result in results) == 1
    member = next(result for result in results if isinstance(result, dict))
    assert member["role"] == "member"
    issued = await service.create_key(member, "PostgreSQL fixture")
    with engine.connect() as c:
        assert c.execute(sa.select(sessions.c.token_hash)).scalar_one() == digest(session_token)
        assert c.execute(sa.select(invitations.c.token_hash)).scalar_one() == digest(invitation["token"])
        assert c.execute(sa.select(api_keys.c.key_hash)).scalar_one() == digest(issued["raw_key"])
        for table, raw in ((sessions, session_token), (invitations, invitation["token"]), (api_keys, issued["raw_key"])):
            assert raw not in repr(list(c.execute(sa.select(table)).mappings()))
    # Database-level immutable username and restrictive deletion, not only service assertions.
    for operation in (users.update().where(users.c.id == member["id"]).values(username="changed_member"),
                      users.delete().where(users.c.id == member["id"])):
        try:
            with engine.begin() as c:
                c.execute(operation)
        except sa.exc.DBAPIError:
            pass
        else:
            raise AssertionError("Identity database constraint missing")
    engine.dispose()
    fresh = IdentityService(IdentityRepository(engine))
    _, session_id = await fresh.authenticate_session(session_token)
    assert (await fresh.verify_key(issued["raw_key"]))["user"]["id"] == member["id"]
    await fresh.logout(session_id)
    await fresh.revoke_key(admin, member["id"], issued["key"]["id"])
    engine.dispose()
    for operation in (fresh.authenticate_session(session_token), fresh.verify_key(issued["raw_key"])):
        try:
            await operation
        except IdentityError:
            pass
        else:
            raise AssertionError("Revoked identity accepted")


def main():
    engine = None
    try:
        url = sa.engine.make_url(Path(os.environ["URUMI_TEST_DATABASE_URL_FILE"]).read_text().strip())
        if (url.host not in {"127.0.0.1", "localhost"} or url.database != "urumi_gateway_fixture"
                or url.drivername != "postgresql+psycopg"):
            raise ValueError("Disposable fixture required")
        engine = make_engine(url)
        if sa.inspect(engine).get_table_names():
            raise ValueError("Empty fixture required")
        migrate(engine)
        asyncio.run(exercise(engine))
        asyncio.run(identity_exercise(engine))
        migrate(engine, "base", down=True)
        migrate(engine)
        print("PASS: PostgreSQL 0001 + 0002 empty migration/schema; registry regressions; Argon2 admin bootstrap; session/invitation/key hash persistence; concurrent single-use invitation; immediate revocation; reconnect persistence; restrictive identity constraints; downgrade/upgrade")
    except Exception:
        print("FAIL: PostgreSQL fixture validation; raw DB details suppressed")
        raise SystemExit(1) from None
    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    main()
