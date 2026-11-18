"""Known rejected keys are audited; credential migration runs before this revision."""
import importlib
from alembic import op
revision = "0004_secret_refs_rejections"
down_revision = "0003_audit"
branch_labels = None
depends_on = None
old = importlib.import_module("migrations.versions.0003_audit")

def change(codes):
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite": op.execute("DROP TRIGGER IF EXISTS audit_identity")
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_constraint("ck_audit_code", type_="check")
        batch.create_check_constraint("ck_audit_code", "error_code IS NULL OR error_code IN (" +
            ",".join("'" + c + "'" for c in sorted(codes)) + ")")
    if dialect == "sqlite":
        changed = " OR ".join("NEW." + f + " IS NOT OLD." + f for f in old.IMMUTABLE)
        op.execute("CREATE TRIGGER audit_identity BEFORE UPDATE ON audit_events WHEN " + changed +
            " OR OLD.outcome != 'started' BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_AUDIT'); END")

def upgrade(): change(old.ERROR_CODES | {"KEY_REJECTED"})
def downgrade():
    # Reject downgrade with new events rather than erase immutable evidence.
    change(old.ERROR_CODES)
