"""Strict write inputs and explicit safe read DTOs; no identity/authorization yet."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool, StrictStr

from .models import Credential, Upstream


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class CredentialInput(Input):
    kind: Literal["bearer", "header"]
    value: SecretStr = Field(min_length=1, max_length=4096)
    header_name: StrictStr | None = None

    def internal(self):
        return Credential(self.kind, self.value.get_secret_value(), self.header_name)


class CreateServer(Input):
    slug: StrictStr
    display_name: StrictStr
    url: StrictStr
    enabled: StrictBool = True
    credential: CredentialInput | None = None


class EditServer(Input):
    display_name: StrictStr | None = None
    url: StrictStr | None = None
    enabled: StrictBool | None = None
    credential: CredentialInput | None = None


class ServerView(BaseModel):
    id: UUID
    slug: str
    display_name: str
    url: str
    enabled: bool
    observed_status: Literal["connected", "unreachable", "unknown"]
    has_credential: bool
    credential_type: Literal["bearer", "header"] | None
    created_at: datetime
    updated_at: datetime
    last_checked: datetime | None
    failure_reason: str | None
    tools: list[dict]
    tools_stale: bool
    tools_last_checked: datetime | None


class Management:
    def __init__(self, gateway):
        self.gateway = gateway
        self.repository = gateway.repository

    async def detail(self, server_id):
        server = await self.repository.get(server_id)
        if server is None:
            raise KeyError("NOT_FOUND")
        health = await self.repository.health(server_id)
        cache = await self.repository.cached_tools(server_id)
        # Explicit projection: never serialize a dataclass or DB row wholesale.
        view = ServerView(id=server.id, slug=server.slug, display_name=server.display_name, url=server.url,
            enabled=server.enabled, observed_status=health.health, has_credential=server.credential is not None,
            credential_type=server.credential.kind if server.credential else None,
            created_at=server.created_at, updated_at=server.updated_at, last_checked=health.checked_at,
            failure_reason=health.error_code, tools=cache["items"],
            tools_stale=not server.enabled or health.health != "connected" or cache["revision"] != server.revision,
            tools_last_checked=cache["checked_at"])
        # Apply the same literal-credential reflection boundary to all management output.
        await self.gateway._safe(view.model_dump(mode="json"))
        return view

    async def list(self):
        return [await self.detail(s.id) for s in await self.repository.list()]

    async def create(self, body):
        server = Upstream(body.slug, body.display_name, body.url, enabled=body.enabled,
                          credential=body.credential.internal() if body.credential else None)
        if await self.repository.get_by_slug(server.slug):
            raise ValueError("DUPLICATE_REGISTRATION")
        # Reject credential reflection in URL/name even before persistence.
        if server.credential and server.credential.value in (server.url + server.display_name + server.slug):
            raise ValueError("INVALID_REGISTRATION")
        await self.repository.add(server)
        return await self.detail(server.id)

    async def edit(self, server_id, body):
        current = await self.repository.get(server_id)
        if current is None:
            raise KeyError("NOT_FOUND")
        changes = {key: getattr(body, key) for key in body.model_fields_set}
        if any(value is None for key, value in changes.items() if key != "credential"):
            raise ValueError("INVALID_REGISTRATION")
        if "credential" in changes:
            changes["credential"] = body.credential.internal() if body.credential else None
        from dataclasses import replace
        updated = replace(current, **changes)
        credential = updated.credential
        if credential and credential.value in (updated.url + updated.display_name + updated.slug):
            raise ValueError("INVALID_REGISTRATION")
        await self.repository.edit(server_id, **changes)
        return await self.detail(server_id)

    async def remove(self, server_id):
        if await self.repository.get(server_id) is None:
            raise KeyError("NOT_FOUND")
        await self.repository.remove(server_id)

    async def refresh(self, server_id):
        server = await self.repository.get(server_id)
        if server is None:
            raise KeyError("NOT_FOUND")
        # Disabled refresh is a read-only no-op, not a hidden connection.
        await self.gateway.refresh(server)
        return await self.detail(server_id)
