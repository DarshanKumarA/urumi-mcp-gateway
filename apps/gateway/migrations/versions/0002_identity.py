"""Explicit identity schema; registry migration remains unchanged."""
from alembic import op
import sqlalchemy as sa

revision = "0002_identity"
down_revision = "0001_registry"
branch_labels = None
depends_on = None

metadata = sa.MetaData()
users = sa.Table("users", metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("username", sa.String(64), nullable=False, unique=True),
    sa.Column("role", sa.String(10), nullable=False),
    sa.Column("password_hash", sa.Text, nullable=False),
    sa.Column("enabled", sa.Boolean, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("role IN ('admin','member')", name="ck_user_role"))
sessions = sa.Table("sessions", metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("revoked_at", sa.DateTime(timezone=True)))
invitations = sa.Table("invitations", metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("username", sa.String(64), nullable=False),
    sa.Column("role", sa.String(10), nullable=False),
    sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
    sa.Column("created_by", sa.Uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("accepted_at", sa.DateTime(timezone=True)),
    sa.Column("revoked_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("role = 'member'", name="ck_invitation_member"))
api_keys = sa.Table("api_keys", metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    sa.Column("label", sa.String(100), nullable=False),
    sa.Column("prefix", sa.String(32), nullable=False),
    sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("revoked_at", sa.DateTime(timezone=True)))


def upgrade():
    metadata.create_all(op.get_bind(), checkfirst=False)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION immutable_user_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF NEW.id IS DISTINCT FROM OLD.id OR NEW.username IS DISTINCT FROM OLD.username THEN
        RAISE EXCEPTION 'IMMUTABLE_USER_IDENTITY'; END IF; RETURN NEW; END $$""")
        op.execute("CREATE TRIGGER user_identity BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION immutable_user_identity()")
    else:
        op.execute("""CREATE TRIGGER user_identity BEFORE UPDATE ON users
        WHEN NEW.id != OLD.id OR NEW.username != OLD.username
        BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_USER_IDENTITY'); END""")


def downgrade():
    metadata.drop_all(op.get_bind(), checkfirst=False)
    op.execute("DELETE FROM registry_bootstrap WHERE name = 'identity-admin-v1'")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION immutable_user_identity()")
