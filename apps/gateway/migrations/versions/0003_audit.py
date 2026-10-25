"""Durable attribution; identity and registry snapshots remain frozen."""
import sqlalchemy as sa
from alembic import op

revision = "0003_audit"
down_revision = "0002_identity"
branch_labels = None
depends_on = None
metadata = sa.MetaData()
# Reference existing tables for FK compilation; never create/alter them here.
sa.Table("users", metadata, sa.Column("id", sa.Uuid, primary_key=True))
sa.Table("api_keys", metadata, sa.Column("id", sa.Uuid, primary_key=True))

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

IMMUTABLE = ("id", "user_id", "username", "api_key_id", "auth_source", "server_id", "server_slug", "started_at")


def upgrade():
    audit_events.create(op.get_bind(), checkfirst=False)
    if op.get_bind().dialect.name == "postgresql":
        changed = " OR ".join("NEW." + f + " IS DISTINCT FROM OLD." + f for f in IMMUTABLE)
        op.execute("CREATE FUNCTION immutable_audit_identity() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN IF " + changed + " OR OLD.outcome != 'started' THEN RAISE EXCEPTION 'IMMUTABLE_AUDIT'; "
            "END IF; RETURN NEW; END $$")
        op.execute("CREATE TRIGGER audit_identity BEFORE UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION immutable_audit_identity()")
    else:
        changed = " OR ".join("NEW." + f + " IS NOT OLD." + f for f in IMMUTABLE)
        op.execute("CREATE TRIGGER audit_identity BEFORE UPDATE ON audit_events WHEN " + changed +
            " OR OLD.outcome != 'started' BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_AUDIT'); END")


def downgrade():
    audit_events.drop(op.get_bind(), checkfirst=False)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION immutable_audit_identity()")
