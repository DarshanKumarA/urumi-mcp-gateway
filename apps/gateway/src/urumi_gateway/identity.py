"""Identity services: no raw token persistence, no browser-supplied identity."""
import asyncio
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError


class IdentityError(Exception):
    def __init__(self, code="UNAUTHENTICATED", status=401):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class AuthConfig:
    origin: str = "http://127.0.0.1:8000"
    secure_cookie: bool = False
    production: bool = False
    session_seconds: int = 28800
    invitation_seconds: int = 86400
    cookie_name: str = "urumi_session"

    def __post_init__(self):
        try:
            u = urlsplit(self.origin)
            valid = (u.scheme in {"http", "https"} and u.hostname and u.port != 0
                     and not u.username and not u.password and not u.path and not u.query and not u.fragment
                     and not any(ch.isspace() or ord(ch) < 32 for ch in self.origin))
        except ValueError:
            valid = False
        if (not valid or type(self.session_seconds) is not int or not 300 <= self.session_seconds <= 86400
                or type(self.invitation_seconds) is not int or not 300 <= self.invitation_seconds <= 604800
                or self.cookie_name != "urumi_session"
                or (self.production and (not self.secure_cookie or u.scheme != "https"))):
            raise ValueError("AUTH_CONFIGURATION_INVALID")


def username(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{2,63}", value):
        raise ValueError("INVALID_USERNAME")
    return value


def password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        raise ValueError("INVALID_PASSWORD")
    return value


def digest(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def token(kind):
    return f"urumi_{kind}_" + secrets.token_urlsafe(32)


def valid_token(raw, kind):
    return isinstance(raw, str) and re.fullmatch(r"urumi_" + kind + r"_[A-Za-z0-9_-]{43}", raw) is not None


class Passwords:
    def __init__(self):
        self.hasher = PasswordHasher()
        self.dummy = self.hasher.hash(secrets.token_urlsafe(32))
        # Bound local hashing memory pressure without weakening Argon2 parameters.
        self.slots = asyncio.Semaphore(2)

    async def hash(self, raw):
        password(raw)
        async with self.slots:
            return await asyncio.to_thread(self.hasher.hash, raw)

    async def verify(self, encoded, raw):
        def verify():
            try:
                return self.hasher.verify(encoded or self.dummy, raw)
            except (VerificationError, InvalidHashError):
                return False
        async with self.slots:
            return await asyncio.to_thread(verify)


class IdentityService:
    def __init__(self, repository, config=None, *, passwords=None, clock=None):
        self.repo = repository
        self.config = config or AuthConfig()
        self.passwords = passwords or Passwords()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def bootstrap_admin(self, name, raw_password):
        return await self.repo.bootstrap_admin(username(name), await self.passwords.hash(raw_password))

    async def login(self, name, raw_password):
        # Same public failure and one Argon2 verification for unknown/disabled/wrong-password users.
        row = await self.repo.user_for_login(name)
        valid = await self.passwords.verify(row["password_hash"] if row else None, raw_password)
        if not row or not valid or not row["enabled"]:
            raise IdentityError()
        raw = token("session")
        now = self.clock()
        await self.repo.create_session(row["id"], digest(raw), now,
                                       now + timedelta(seconds=self.config.session_seconds))
        return await self.repo.user(row["id"]), raw

    async def authenticate_session(self, raw):
        if not valid_token(raw, "session"):
            raise IdentityError()
        result = await self.repo.session_identity(digest(raw), self.clock())
        if result is None:
            raise IdentityError()
        return result

    async def logout(self, session_id):
        await self.repo.revoke_session(session_id, self.clock())

    @staticmethod
    def require_admin(user):
        if user["role"] != "admin":
            raise IdentityError("FORBIDDEN", 403)

    async def invite(self, actor, name):
        self.require_admin(actor)
        raw, now = token("invite"), self.clock()
        row = await self.repo.create_invitation(username(name), actor["id"], digest(raw), now,
            now + timedelta(seconds=self.config.invitation_seconds))
        return {"invitation": row, "token": raw}

    async def accept(self, raw, raw_password):
        if not valid_token(raw, "invite"):
            raise IdentityError("INVITATION_INVALID", 400)
        encoded = await self.passwords.hash(raw_password)
        try:
            return await self.repo.accept_invitation(digest(raw), encoded, self.clock())
        except ValueError:
            raise IdentityError("INVITATION_INVALID", 400) from None

    async def create_key(self, actor, label):
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 100:
            raise ValueError("INVALID_LABEL")
        raw = token("key")
        row = await self.repo.create_key(actor["id"], label.strip(), raw[:18], digest(raw), self.clock())
        return {"key": row, "raw_key": raw}

    async def verify_key(self, raw):
        if not valid_token(raw, "key"):
            raise IdentityError()
        hashed = digest(raw)
        result = await self.repo.key_identity(hashed)
        if result is None or not hmac.compare_digest(result[2], hashed):
            raise IdentityError()
        return {"user": result[0], "key_id": result[1]}

    async def revoke_key(self, actor, owner, key_id):
        if actor["id"] != owner:
            self.require_admin(actor)
        await self.repo.revoke_key(owner, key_id, self.clock())
