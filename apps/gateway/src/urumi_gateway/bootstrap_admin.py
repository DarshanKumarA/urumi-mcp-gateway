"""Explicit operator command. Password and database URL are read only from files."""
import asyncio
import os
from pathlib import Path

from .database import make_engine
from .identity import IdentityService
from .identity_repository import IdentityRepository


async def bootstrap():
    engine = None
    try:
        url = Path(os.environ["URUMI_DATABASE_URL_FILE"]).read_text(encoding="utf-8").strip()
        # Bound file read; remove one terminal newline, not password whitespace.
        with Path(os.environ["URUMI_BOOTSTRAP_PASSWORD_FILE"]).open(encoding="utf-8") as stream:
            raw = stream.read(1025).removesuffix("\n")
        engine = make_engine(url)
        await IdentityService(IdentityRepository(engine)).bootstrap_admin(
            os.environ["URUMI_BOOTSTRAP_USERNAME"], raw)
        print("Bootstrap administrator ready; existing password preserved.")
    except Exception:
        print("BOOTSTRAP_ADMIN_FAILED; no credential details emitted.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(bootstrap()))
