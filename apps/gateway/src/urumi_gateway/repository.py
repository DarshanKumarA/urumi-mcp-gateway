"""Async repository seam for later PostgreSQL; no database required by protocol tests."""

from dataclasses import replace
from typing import Protocol
from uuid import UUID

from .models import Observation, Upstream


class UpstreamRepository(Protocol):
    async def list(self) -> list[Upstream]: ...
    async def get(self, server_id: UUID) -> Upstream | None: ...
    async def add(self, server: Upstream) -> None: ...
    async def edit(self, server_id: UUID, **changes) -> Upstream: ...
    async def remove(self, server_id: UUID) -> None: ...
    async def observe(self, server: Upstream, observation: Observation) -> bool: ...
    async def health(self, server_id: UUID) -> Observation: ...


class MemoryRepository:
    def __init__(self):
        self._servers = {}
        self._health = {}
        self._used_ids = set()

    async def list(self):
        return sorted(self._servers.values(), key=lambda server: server.slug)

    async def get(self, server_id):
        return self._servers.get(server_id)

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
        updated = replace(server, **changes, revision=server.revision + 1)
        self._servers[server_id] = updated
        self._health[server_id] = Observation()
        return updated

    async def remove(self, server_id):
        self._servers.pop(server_id, None)
        self._health.pop(server_id, None)

    async def observe(self, server, observation):
        # Ignore completion of an old request after edit/disable/remove.
        if self._servers.get(server.id) != server:
            return False
        self._health[server.id] = observation
        return True

    async def health(self, server_id):
        return self._health.get(server_id, Observation())
