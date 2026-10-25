"""Durable minimal audit metadata; never accepts tool payloads or credentials."""
from uuid import uuid4
import sqlalchemy as sa

from .database import SQLRepository, metadata, utc
from . import identity_repository  # Register referenced identity tables.

ERROR_CODES = frozenset({"UNKNOWN_TOOL", "UPSTREAM_DISABLED", "UPSTREAM_CHANGED",
    "UPSTREAM_UNAVAILABLE", "UPSTREAM_TIMEOUT", "UPSTREAM_REDIRECT", "UPSTREAM_INVALID_RESPONSE",
    "UPSTREAM_UNSAFE_RESPONSE", "UPSTREAM_TOOL_ERROR", "VALIDATION_ERROR", "GATEWAY_FAILURE",
    "AUDIT_UNAVAILABLE"})

audit_events = sa.Table("audit_events", metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    sa.Column("username", sa.String(64), nullable=False),
    sa.Column("api_key_id", sa.Uuid, sa.ForeignKey("api_keys.id", ondelete="RESTRICT")),
    sa.Column("auth_source", sa.String(16), nullable=False),
    # Historical UUID snapshot deliberately has no live-registration FK:
    # removing a registration must not erase or rewrite attribution.
    sa.Column("server_id", sa.Uuid),
    sa.Column("server_slug", sa.String(32)),
    sa.Column("gateway_tool", sa.String(128), nullable=False),
    sa.Column("upstream_tool", sa.String(128)),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("completed_at", sa.DateTime(timezone=True)),
    sa.Column("duration_ms", sa.BigInteger),
    sa.Column("outcome", sa.String(16), nullable=False),
    sa.Column("error_code", sa.String(64)),
    sa.CheckConstraint("(auth_source = 'api_key' AND api_key_id IS NOT NULL) OR "
                       "(auth_source = 'session' AND api_key_id IS NULL)", name="ck_audit_source"),
    sa.CheckConstraint("(outcome = 'started' AND completed_at IS NULL AND duration_ms IS NULL AND error_code IS NULL) OR "
                       "(outcome = 'succeeded' AND completed_at IS NOT NULL AND duration_ms >= 0 AND duration_ms IS NOT NULL AND error_code IS NULL) OR "
                       "(outcome = 'failed' AND completed_at IS NOT NULL AND duration_ms >= 0 AND duration_ms IS NOT NULL AND error_code IS NOT NULL)", name="ck_audit_outcome"),
    sa.CheckConstraint("error_code IS NULL OR error_code IN (" + ",".join("'" + c + "'" for c in sorted(ERROR_CODES)) + ")", name="ck_audit_code"))
sa.Index("ix_audit_started_id", audit_events.c.started_at, audit_events.c.id)
sa.Index("ix_audit_user_started", audit_events.c.user_id, audit_events.c.started_at)


class AuditUnavailable(Exception):
    def __init__(self):
        super().__init__("AUDIT_UNAVAILABLE")


class AuditRepository(SQLRepository):
    async def _audit(self, operation):
        try:
            return await self._run(operation)
        except Exception:
            raise AuditUnavailable() from None

    async def start(self, principal, target, now):
        event_id = uuid4()
        row = dict(id=event_id, user_id=principal.user_id, username=principal.username,
            api_key_id=principal.api_key_id, auth_source=principal.source,
            server_id=target["server_id"], server_slug=target["server_slug"],
            gateway_tool=target["gateway_tool"], upstream_tool=target.get("upstream_tool"), started_at=now,
            completed_at=None, duration_ms=None, outcome="started", error_code=None)
        # _run exits its transaction (COMMIT) before returning the UUID.
        await self._audit(lambda c: c.execute(audit_events.insert().values(**row)))
        return event_id

    async def bind_tool(self, event_id, gateway_name, original_name):
        def bind(c):
            result = c.execute(audit_events.update().where(audit_events.c.id == event_id,
                audit_events.c.outcome == "started", sa.or_(audit_events.c.upstream_tool.is_(None),
                    audit_events.c.upstream_tool == original_name))
                .values(gateway_tool=gateway_name, upstream_tool=original_name))
            if result.rowcount != 1:
                raise AuditUnavailable()
        await self._audit(bind)

    async def finish(self, event_id, outcome, code, completed, duration_ms):
        if outcome not in {"succeeded", "failed"} or (code is not None and code not in ERROR_CODES):
            raise AuditUnavailable()
        def finish(c):
            result = c.execute(audit_events.update().where(audit_events.c.id == event_id,
                audit_events.c.outcome == "started").values(outcome=outcome, error_code=code,
                    completed_at=completed, duration_ms=duration_ms))
            if result.rowcount != 1:
                raise AuditUnavailable()
        await self._audit(finish)

    async def list_events(self, *, page=1, per_page=20, user_id=None, server_slug=None, tool=None, outcome=None):
        if not 1 <= page <= 100000 or not 1 <= per_page <= 100:
            raise ValueError("VALIDATION_ERROR")
        conditions = []
        for column, value in ((audit_events.c.user_id, user_id), (audit_events.c.server_slug, server_slug),
                              (audit_events.c.gateway_tool, tool), (audit_events.c.outcome, outcome)):
            if value is not None:
                conditions.append(column == value)
        def read(c):
            total = c.execute(sa.select(sa.func.count()).select_from(audit_events).where(*conditions)).scalar_one()
            rows = c.execute(sa.select(audit_events).where(*conditions)
                .order_by(audit_events.c.started_at.desc(), audit_events.c.id.desc())
                .limit(per_page).offset((page - 1) * per_page)).mappings()
            items = [{k: utc(v) if k.endswith("_at") else v for k, v in row.items()} for row in rows]
            return dict(items=items, page=page, per_page=per_page, total=total,
                        has_more=page * per_page < total)
        return await self._audit(read)
