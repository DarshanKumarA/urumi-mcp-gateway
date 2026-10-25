"""Identity persistence; secrets stay inside this repository/service boundary."""
from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa

from .database import SQLRepository, metadata, bootstrap, utc

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

USER_FIELDS = ("id", "username", "role", "enabled", "created_at", "updated_at")
KEY_FIELDS = ("id", "user_id", "label", "prefix", "created_at", "revoked_at")
INVITE_FIELDS = ("id", "username", "role", "created_by", "created_at", "expires_at", "accepted_at", "revoked_at")


def selected(row, fields):
    return {key: utc(row[key]) if isinstance(row[key], datetime) else row[key] for key in fields}


class IdentityRepository(SQLRepository):
    """Reuse bounded transactions/error sanitization, without exposing registry APIs to routes."""
    async def user_for_login(self, username):
        return await self._run(lambda c: c.execute(sa.select(users).where(
            users.c.username == username)).mappings().first())

    async def user(self, user_id):
        def read(c):
            row = c.execute(sa.select(users).where(users.c.id == user_id)).mappings().first()
            if row is None:
                raise KeyError("NOT_FOUND")
            return selected(row, USER_FIELDS)
        return await self._run(read)

    async def list_users(self):
        return await self._run(lambda c: [selected(r, USER_FIELDS) for r in c.execute(
            sa.select(users).order_by(users.c.username)).mappings()])

    async def bootstrap_admin(self, username, password_hash):
        def create(c):
            # One durable receipt serializes concurrent first-admin attempts.
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            insert = pg_insert if c.dialect.name == "postgresql" else sqlite_insert
            claimed = c.execute(insert(bootstrap).values(name="identity-admin-v1")
                .on_conflict_do_nothing().returning(bootstrap.c.name)).first()
            existing = c.execute(sa.select(users).where(users.c.username == username)).mappings().first()
            if not claimed:
                if existing and existing["role"] == "admin" and existing["enabled"]:
                    return selected(existing, USER_FIELDS)
                raise ValueError("BOOTSTRAP_CONFLICT")
            if existing or c.execute(sa.select(users.c.id).where(users.c.role == "admin")).first():
                raise ValueError("BOOTSTRAP_CONFLICT")
            now = datetime.now(timezone.utc)
            row = dict(id=uuid4(), username=username, role="admin", password_hash=password_hash,
                       enabled=True, created_at=now, updated_at=now)
            c.execute(users.insert().values(**row))
            return selected(row, USER_FIELDS)
        return await self._run(create)

    async def create_session(self, user_id, token_hash, now, expires):
        await self._run(lambda c: c.execute(sessions.insert().values(id=uuid4(), user_id=user_id,
            token_hash=token_hash, created_at=now, expires_at=expires)))

    async def session_identity(self, token_hash, now):
        def read(c):
            row = c.execute(sa.select(users, sessions.c.id.label("session_id"))
                .join(sessions, sessions.c.user_id == users.c.id)
                .where(sessions.c.token_hash == token_hash, sessions.c.revoked_at.is_(None),
                       sessions.c.expires_at > now, users.c.enabled.is_(True))).mappings().first()
            return (selected(row, USER_FIELDS), row["session_id"]) if row else None
        return await self._run(read)

    async def revoke_session(self, session_id, now):
        await self._run(lambda c: c.execute(sessions.update().where(sessions.c.id == session_id,
            sessions.c.revoked_at.is_(None)).values(revoked_at=now)))

    async def create_invitation(self, username, creator, token_hash, now, expires):
        def create(c):
            if c.execute(sa.select(users.c.id).where(users.c.username == username)).first():
                raise ValueError("IDENTITY_CONFLICT")
            row = dict(id=uuid4(), username=username, role="member", token_hash=token_hash,
                       created_by=creator, created_at=now, expires_at=expires, accepted_at=None, revoked_at=None)
            c.execute(invitations.insert().values(**row))
            return selected(row, INVITE_FIELDS)
        return await self._run(create)

    async def accept_invitation(self, token_hash, password_hash, now):
        def accept(c):
            # Conditional UPDATE is the single-use claim on SQLite and PostgreSQL.
            row = c.execute(invitations.update().where(invitations.c.token_hash == token_hash,
                invitations.c.accepted_at.is_(None), invitations.c.revoked_at.is_(None),
                invitations.c.expires_at > now, invitations.c.role == "member")
                .values(accepted_at=now).returning(invitations.c.username)).first()
            if row is None:
                raise ValueError("INVITATION_INVALID")
            member = dict(id=uuid4(), username=row[0], role="member", password_hash=password_hash,
                          enabled=True, created_at=now, updated_at=now)
            c.execute(users.insert().values(**member))
            return selected(member, USER_FIELDS)
        return await self._run(accept)

    async def list_invitations(self):
        return await self._run(lambda c: [selected(r, INVITE_FIELDS) for r in c.execute(
            sa.select(invitations).order_by(invitations.c.created_at)).mappings()])

    async def revoke_invitation(self, invitation_id, now):
        await self._run(lambda c: c.execute(invitations.update().where(invitations.c.id == invitation_id,
            invitations.c.revoked_at.is_(None)).values(revoked_at=now)))

    async def create_key(self, user_id, label, prefix, key_hash, now):
        row = dict(id=uuid4(), user_id=user_id, label=label, prefix=prefix, key_hash=key_hash,
                   created_at=now, revoked_at=None)
        await self._run(lambda c: c.execute(api_keys.insert().values(**row)))
        return selected(row, KEY_FIELDS)

    async def list_keys(self, user_id):
        return await self._run(lambda c: [selected(r, KEY_FIELDS) for r in c.execute(
            sa.select(api_keys).where(api_keys.c.user_id == user_id).order_by(api_keys.c.created_at)).mappings()])

    async def revoke_key(self, user_id, key_id, now):
        def revoke(c):
            row = c.execute(sa.select(api_keys.c.id).where(api_keys.c.id == key_id,
                api_keys.c.user_id == user_id)).first()
            if row is None:
                raise KeyError("NOT_FOUND")
            c.execute(api_keys.update().where(api_keys.c.id == key_id,
                api_keys.c.revoked_at.is_(None)).values(revoked_at=now))
        await self._run(revoke)

    async def key_identity(self, key_hash):
        def read(c):
            row = c.execute(sa.select(users, api_keys.c.id.label("key_id"), api_keys.c.key_hash)
                .join(api_keys, api_keys.c.user_id == users.c.id).where(api_keys.c.key_hash == key_hash,
                    api_keys.c.revoked_at.is_(None), users.c.enabled.is_(True))).mappings().first()
            return (selected(row, USER_FIELDS), row["key_id"], row["key_hash"]) if row else None
        return await self._run(read)

    async def set_member_enabled(self, user_id, enabled):
        def change(c):
            result = c.execute(users.update().where(users.c.id == user_id, users.c.role == "member")
                .values(enabled=enabled, updated_at=datetime.now(timezone.utc)))
            if result.rowcount != 1:
                raise KeyError("NOT_FOUND")
        await self._run(change)
