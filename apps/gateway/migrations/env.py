"""Explicit migration connection; no credentials in configuration or logging."""
import os
from pathlib import Path

from alembic import context
from urumi_gateway.database import metadata, make_engine
from urumi_gateway import identity_repository  # Register identity metadata for schema checks.

config = context.config


def migrate(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url="postgresql+psycopg://", target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    migrate(config.attributes["connection"])
else:
    try:
        url = Path(os.environ["URUMI_DATABASE_URL_FILE"]).read_text(encoding="utf-8").strip()
        engine = make_engine(url)
        with engine.connect() as connection:
            migrate(connection)
        engine.dispose()
    except Exception:
        raise RuntimeError("MIGRATION_FAILED") from None
