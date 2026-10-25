"""Initial registry, health/cache and one-time seed receipt. Frozen schema snapshot."""
from alembic import op
import sqlalchemy as sa

revision = "0001_registry"
down_revision = None
branch_labels = None
depends_on = None

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



def upgrade():
    bind = op.get_bind()
    metadata.create_all(bind, checkfirst=False)
    if bind.dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION prevent_registry_identity_change() RETURNS trigger AS $$
        BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id OR NEW.slug IS DISTINCT FROM OLD.slug THEN
            RAISE EXCEPTION 'IMMUTABLE_REGISTRATION_IDENTITY';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER immutable_registry_identity BEFORE UPDATE ON mcp_servers
        FOR EACH ROW EXECUTE FUNCTION prevent_registry_identity_change()""")
    elif bind.dialect.name == "sqlite":
        op.execute("""CREATE TRIGGER immutable_registry_identity BEFORE UPDATE OF id, slug ON mcp_servers
        WHEN NEW.id != OLD.id OR NEW.slug != OLD.slug
        BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_REGISTRATION_IDENTITY'); END""")


def downgrade():
    # Explicit operator command only; destructive to registry/credential/cache data.
    bind = op.get_bind()
    metadata.drop_all(bind, checkfirst=False)
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION prevent_registry_identity_change()")
