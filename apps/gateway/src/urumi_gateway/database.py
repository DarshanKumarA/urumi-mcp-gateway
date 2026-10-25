"""SQLAlchemy repository. Blocking DB work runs in worker threads, never on ASGI's loop."""

import asyncio
import logging
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid5, NAMESPACE_URL

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import Credential, Observation, Upstream

metadata = sa.MetaData()
servers = sa.Table(
    "mcp_servers", metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("slug", sa.String(32), nullable=False, unique=True),
    sa.Column("display_name", sa.String(100), nullable=False),
    sa.Column("url", sa.String(2048), nullable=False),
    sa.Column("enabled", sa.Boolean, nullable=False),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("credential_type", sa.String(10)),
    sa.Column("credential_header", sa.String(64)),
    sa.Column("credential_value", sa.Text),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("observed_status", sa.String(16), nullable=False),
    sa.Column("last_checked", sa.DateTime(timezone=True)),
    sa.Column("error_code", sa.String(64)),
    sa.Column("tools", sa.JSON, nullable=False),
    sa.Column("tools_revision", sa.Integer),
    sa.Column("tools_checked_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("observed_status IN ('unknown','connected','unreachable')", name="ck_server_health"),
    sa.CheckConstraint("revision >= 0", name="ck_server_revision"),
    sa.CheckConstraint("(credential_type IS NULL AND credential_header IS NULL AND credential_value IS NULL) OR "
                       "(credential_type IS NOT NULL AND credential_type = 'bearer' AND credential_header IS NULL AND credential_value IS NOT NULL) OR "
                       "(credential_type IS NOT NULL AND credential_type = 'header' AND credential_header IS NOT NULL AND credential_value IS NOT NULL)",
                       name="ck_server_credential"),
)
# Receipt survives removal: startup does not resurrect an administrator-deleted seed.
bootstrap = sa.Table("registry_bootstrap", metadata, sa.Column("name", sa.String(64), primary_key=True))


class RepositoryUnavailable(Exception):
    def __init__(self):
        super().__init__("REGISTRY_UNAVAILABLE")


def make_engine(url):
    if sa.engine.make_url(url).drivername != "postgresql+psycopg":
        raise ValueError("POSTGRESQL_REQUIRED")
    # Suppress SQL statement/result logging even if a caller raises log verbosity.
    # hide_parameters alone does not suppress DEBUG row output.
    engine = sa.create_engine(url, echo=False, hide_parameters=True, pool_pre_ping=True,
                            pool_size=5, max_overflow=0, pool_timeout=5,
                            connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"})
    class Discard(logging.Filter):
        def filter(self, record):
            return False
    for name in set(logging.Logger.manager.loggerDict) | {"sqlalchemy.engine.Engine", "sqlalchemy.pool.impl.QueuePool"}:
        if name.startswith(("sqlalchemy.engine", "sqlalchemy.pool")):
            logging.getLogger(name).addFilter(Discard())
    return engine


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def registration(row):
    credential = (Credential(row["credential_type"], row["credential_value"], row["credential_header"])
                  if row["credential_type"] else None)
    return Upstream(id=row["id"], slug=row["slug"], display_name=row["display_name"], url=row["url"],
                    enabled=row["enabled"], revision=row["revision"], credential=credential,
                    created_at=utc(row["created_at"]), updated_at=utc(row["updated_at"]))


def values(server):
    c = server.credential
    return dict(id=server.id, slug=server.slug, display_name=server.display_name, url=server.url,
                enabled=server.enabled, revision=server.revision,
                credential_type=c.kind if c else None, credential_header=c.header_name if c else None,
                credential_value=c.value if c else None, created_at=server.created_at,
                updated_at=server.updated_at)


class SQLRepository:
    def __init__(self, engine):
        self.engine = engine

    async def _run(self, operation):
        def transaction():
            try:
                with self.engine.begin() as conn:
                    return operation(conn)
            except IntegrityError:
                raise ValueError("REGISTRY_CONFLICT") from None
            except SQLAlchemyError:
                raise RepositoryUnavailable() from None
        return await asyncio.to_thread(transaction)

    async def list(self):
        return await self._run(lambda c: [registration(r) for r in c.execute(
            sa.select(servers).order_by(servers.c.slug)).mappings()])

    async def get(self, server_id):
        return await self._get(servers.c.id == server_id)

    async def get_by_slug(self, slug):
        return await self._get(servers.c.slug == slug)

    async def _get(self, predicate):
        def read(c):
            row = c.execute(sa.select(servers).where(predicate)).mappings().first()
            return registration(row) if row else None
        return await self._run(read)

    async def add(self, server):
        def insert(c):
            if c.execute(sa.select(servers.c.id).where(servers.c.slug == server.slug)).first():
                raise ValueError("DUPLICATE_REGISTRATION")
            c.execute(servers.insert().values(**values(server), observed_status="unknown", tools=[]))
        await self._run(insert)

    async def edit(self, server_id, **changes):
        if not changes.keys() <= {"display_name", "url", "enabled", "credential"}:
            raise ValueError("IMMUTABLE_OR_UNKNOWN_FIELD")
        def edit(c):
            row = c.execute(sa.select(servers).where(servers.c.id == server_id).with_for_update()).mappings().first()
            if row is None:
                raise KeyError("NOT_FOUND")
            current = registration(row)
            updated = replace(current, **changes, revision=current.revision + 1, updated_at=datetime.now(timezone.utc))
            fields = values(updated)
            for key in ("id", "slug", "created_at"):
                fields.pop(key)
            # Any configuration edit invalidates metadata, including possible old credential reflections.
            c.execute(servers.update().where(servers.c.id == server_id).values(
                **fields, observed_status="unknown", last_checked=None, error_code=None,
                tools=[], tools_revision=None, tools_checked_at=None))
            return updated
        return await self._run(edit)

    async def remove(self, server_id):
        await self._run(lambda c: c.execute(servers.delete().where(servers.c.id == server_id)))

    async def observe(self, server, observation, *, tools=None):
        now = datetime.now(timezone.utc)
        fields = dict(observed_status=observation.health, error_code=observation.error_code, last_checked=now)
        if tools is not None:
            fields.update(tools=tools, tools_revision=server.revision, tools_checked_at=now)
        def observe(c):
            return c.execute(servers.update().where(servers.c.id == server.id,
                servers.c.revision == server.revision).values(**fields)).rowcount == 1
        return await self._run(observe)

    async def health(self, server_id):
        def read(c):
            row = c.execute(sa.select(servers.c.observed_status, servers.c.error_code, servers.c.last_checked)
                            .where(servers.c.id == server_id)).first()
            return Observation(row[0], row[1], utc(row[2])) if row else Observation()
        return await self._run(read)

    async def cached_tools(self, server_id):
        def read(c):
            row = c.execute(sa.select(servers.c.tools, servers.c.tools_revision, servers.c.tools_checked_at)
                            .where(servers.c.id == server_id)).first()
            return {"items": row[0], "revision": row[1], "checked_at": utc(row[2])} if row else {
                "items": [], "revision": None, "checked_at": None}
        return await self._run(read)

    async def seed_woocommerce(self):
        def seed(c):
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            insert = pg_insert if c.dialect.name == "postgresql" else sqlite_insert
            first = c.execute(insert(bootstrap).values(name="woocommerce-v1")
                              .on_conflict_do_nothing().returning(bootstrap.c.name)).first()
            if first:
                server = Upstream("woocommerce", "WooCommerce",
                    "http://urumi-woo-mcp.urumi.svc.cluster.local:8000/mcp",
                    id=uuid5(NAMESPACE_URL, "urumi:upstream:woocommerce"))
                c.execute(insert(servers).values(**values(server), observed_status="unknown", tools=[])
                          .on_conflict_do_nothing())
        await self._run(seed)
