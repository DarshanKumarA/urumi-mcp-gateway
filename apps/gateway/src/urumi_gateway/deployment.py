"""Explicit deployment commands. No DDL, password reset or seed at server startup."""
import asyncio
import os
from pathlib import Path
import re
import sys
import time
from uuid import uuid5, NAMESPACE_URL

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa

from .database import SQLRepository, make_engine, bootstrap
from .identity import IdentityService
from .identity_repository import IdentityRepository
from .models import Upstream, Credential

RECEIPTS = {"identity-admin-v1", "woocommerce-v1", "arithmetic-v1", "store_policy-v1"}


def read_file(variable, limit=4096):
    with Path(os.environ[variable]).open(encoding="utf-8") as stream:
        value = stream.read(limit + 2).removesuffix("\n")
    if not value or len(value) > limit:
        raise ValueError("DEPLOYMENT_CONFIGURATION_INVALID")
    return value


def database_ready(engine, phase="ready"):
    """Read only. Schema/bootstrap receipt checks never contact upstreams/provider."""
    try:
        with engine.connect() as connection:
            connection.execute(sa.text("SELECT 1"))
            if phase == "database":
                return True
            expected = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
            if connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() != expected:
                return False
            if phase == "schema":
                return True
            return RECEIPTS <= set(connection.execute(sa.select(bootstrap.c.name)).scalars())
    except Exception:
        return False


def wait_for(engine, phase, seconds=300):
    deadline = time.monotonic() + seconds
    while not database_ready(engine, phase):
        if time.monotonic() >= deadline:
            raise RuntimeError("DEPLOYMENT_DEPENDENCY_TIMEOUT")
        time.sleep(2)


async def seed_builtins(repository, token, urls):
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
        raise ValueError("UPSTREAM_CREDENTIAL_INVALID")
    for slug, name in (("woocommerce", "WooCommerce"), ("arithmetic", "Arithmetic"),
                       ("store_policy", "Store Policy")):
        await repository.seed_registration(Upstream(slug, name, urls[slug],
            credential=Credential("bearer", token) if slug == "woocommerce" else None,
            id=uuid5(NAMESPACE_URL, "urumi:upstream:" + slug)))


async def initialize(engine):
    await IdentityService(IdentityRepository(engine)).bootstrap_admin(
        read_file("URUMI_BOOTSTRAP_USERNAME_FILE", 64), read_file("URUMI_BOOTSTRAP_PASSWORD_FILE", 1024))
    urls = {slug: os.environ[key] for slug, key in (
        ("woocommerce", "URUMI_WOO_MCP_URL"), ("arithmetic", "URUMI_ARITHMETIC_MCP_URL"),
        ("store_policy", "URUMI_STORE_POLICY_MCP_URL"))}
    await seed_builtins(SQLRepository(engine), read_file("URUMI_WOO_MCP_TOKEN_FILE", 256), urls)


def main():
    engine = None
    try:
        mode = sys.argv[1]
        if mode not in {"migrate", "bootstrap", "wait-ready"}:
            raise ValueError()
        engine = make_engine(read_file("URUMI_DATABASE_URL_FILE"))
        if mode == "migrate":
            wait_for(engine, "database")
            cfg = Config("alembic.ini")
            with engine.begin() as connection:
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")
        elif mode == "bootstrap":
            wait_for(engine, "schema")
            asyncio.run(initialize(engine))
        else:
            wait_for(engine, "ready")
        print("DEPLOYMENT_STEP_COMPLETE")
        return 0
    except Exception:
        print("DEPLOYMENT_STEP_FAILED; details suppressed.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
