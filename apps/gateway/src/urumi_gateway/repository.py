"""Shared async repository seam; in-memory implementation for isolated protocol tests."""

from dataclasses import replace
from datetime import datetime, timezone
from copy import deepcopy
from typing import Protocol
from uuid import UUID

from .models import Observation, Upstream


class UpstreamRepository(Protocol):
    async def list(self) -> list[Upstream]: ...
    async def get(self, server_id: UUID) -> Upstream | None: ...
    async def get_by_slug(self, slug: str) -> Upstream | None: ...
    async def add(self, server: Upstream) -> None: ...
    async def edit(self, server_id: UUID, **changes) -> Upstream: ...
    async def remove(self, server_id: UUID) -> None: ...
    async def observe(self, server: Upstream, observation: Observation, *, tools=None) -> bool: ...
    async def health(self, server_id: UUID) -> Observation: ...
    async def cached_tools(self, server_id: UUID) -> dict: ...


class MemoryRepository:
    def __init__(self):
        self._servers = {}
        self._health = {}
        self._used_ids = set()
        self._tools = {}

    async def list(self):
        return sorted(self._servers.values(), key=lambda server: server.slug)

    async def get(self, server_id):
        return self._servers.get(server_id)

    async def get_by_slug(self, slug):
        return next((s for s in self._servers.values() if s.slug == slug), None)

    async def add(self, server):
        if server.id in self._used_ids or any(s.slug == server.slug for s in self._servers.values()):
            raise ValueError("DUPLICATE_REGISTRATION")
        self._servers[server.id] = server
        self._health[server.id] = Observation()
        self._used_ids.add(server.id)

    async def edit(self, server_id, **changes):
        if not changes.keys() <= {"display_name", "url", "enabled", "credential"}:
            raise ValueError("IMMUTABLE_OR_UNKNOWN_FIELD")
        server = self._servers[server_id]
        updated = replace(server, **changes, revision=server.revision + 1, updated_at=datetime.now(timezone.utc))
        self._servers[server_id] = updated
        self._health[server_id] = Observation()
        self._tools.pop(server_id, None)
        return updated

    async def remove(self, server_id):
        self._servers.pop(server_id, None)
        self._health.pop(server_id, None)
        self._tools.pop(server_id, None)

    async def observe(self, server, observation, *, tools=None):
        # Ignore completion of an old request after edit/disable/remove.
        if self._servers.get(server.id) != server:
            return False
        now = datetime.now(timezone.utc)
        self._health[server.id] = replace(observation, checked_at=now)
        if tools is not None:
            self._tools[server.id] = {"items": deepcopy(tools), "revision": server.revision, "checked_at": now}
        return True

    async def health(self, server_id):
        return self._health.get(server_id, Observation())

    async def cached_tools(self, server_id):
        return deepcopy(self._tools.get(server_id, {"items": [], "revision": None, "checked_at": None}))
