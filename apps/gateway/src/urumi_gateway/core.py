"""Concurrent catalogs and exact stored routing; independent of REST/users/chat."""

import asyncio
import copy
import hashlib
import json
import re
from dataclasses import dataclass

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for
from referencing import Registry
from referencing.exceptions import NoSuchResource
from mcp.types import CallToolResult, Tool

from .errors import GatewayError
from .models import Observation, Upstream
from .repository import UpstreamRepository
from .upstream import UpstreamClient


def _no_remote_ref(uri):
    raise NoSuchResource(ref=uri)


def validator(schema):
    chosen = validator_for(schema, default=Draft202012Validator)
    chosen.check_schema(schema)
    return chosen(schema, registry=Registry(retrieve=_no_remote_ref))


def reject_remote_refs(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if key in ("$ref", "$dynamicRef") and not str(value).startswith("#"):
                raise GatewayError("UPSTREAM_INVALID_RESPONSE")
            reject_remote_refs(value)
    elif isinstance(item, list):
        for value in item:
            reject_remote_refs(value)


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)
    elif isinstance(value, str):
        yield value


def exposed_name(slug, original):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", original):
        raise GatewayError("UPSTREAM_INVALID_RESPONSE")
    name = f"{slug}__{original}"
    if len(name) > 128:
        # Shorten only overlong names; hash the complete slug__original content.
        # Ordinary names are unchanged. Always route by
        # the stored original, never reconstruct from the shortened suffix.
        name = name[:111] + "_" + hashlib.sha256(name.encode()).hexdigest()[:16]
    return name


@dataclass
class Catalog:
    registration: Upstream
    tools: dict[str, Tool]
    originals: dict[str, str]
    available: bool = True


class Gateway:
    def __init__(self, repository: UpstreamRepository, upstream=None):
        self.repository = repository
        self.upstream = upstream or UpstreamClient()
        self._catalogs = {}

    async def _safe(self, value):
        strings = list(_walk(value))
        for server in await self.repository.list():
            if server.credential and any(server.credential.value in s for s in strings):
                raise GatewayError("UPSTREAM_UNSAFE_RESPONSE")
        if len(json.dumps(value, ensure_ascii=True).encode()) > 2 * 1024 * 1024:
            raise GatewayError("UPSTREAM_INVALID_RESPONSE")

    async def refresh(self, server):
        if not server.enabled:
            return
        try:
            async with asyncio.timeout(self.upstream.timeouts.discovery):
                await self._refresh(server)
        except TimeoutError:
            if await self.repository.observe(server, Observation("unreachable", "UPSTREAM_TIMEOUT")):
                if server.id in self._catalogs:
                    self._catalogs[server.id].available = False

    async def _refresh(self, server):
        if await self.repository.get(server.id) != server:
            return
        try:
            discovered = await self.upstream.discover(server)
            mapped, originals = {}, {}
            await self._safe([tool.model_dump(mode="json") for tool in discovered])
            for tool in discovered:
                name = exposed_name(server.slug, tool.name)
                if name in mapped:
                    raise GatewayError("UPSTREAM_INVALID_RESPONSE")
                for schema in (tool.input_schema, tool.output_schema):
                    if schema is not None:
                        validator(schema)
                        # Never fetch schema references supplied by an upstream.
                        reject_remote_refs(schema)
                # Explicit supported metadata, no arbitrary extensions/icons,
                # upstream server instructions, request state or task execution.
                mapped[name] = Tool(name=name, title=tool.title, description=tool.description,
                                    input_schema=copy.deepcopy(tool.input_schema),
                                    output_schema=copy.deepcopy(tool.output_schema),
                                    annotations=copy.deepcopy(tool.annotations))
                originals[name] = tool.name
            if await self.repository.observe(server, Observation("connected"),
                                             tools=[t.model_dump(mode="json") for t in mapped.values()]):
                self._catalogs[server.id] = Catalog(server, mapped, originals)
        except Exception as error:
            code = error.code if isinstance(error, GatewayError) else "UPSTREAM_INVALID_RESPONSE"
            if await self.repository.observe(server, Observation("unreachable", code)):
                if server.id in self._catalogs:
                    self._catalogs[server.id].available = False

    async def list_tools(self):
        servers = await self.repository.list()
        await asyncio.gather(*(self.refresh(s) for s in servers if s.enabled))
        result = []
        for server in await self.repository.list():
            catalog = self._catalogs.get(server.id)
            if server.enabled and catalog and catalog.available and catalog.registration == server:
                result.extend(copy.deepcopy(list(catalog.tools.values())))
        return sorted(result, key=lambda tool: tool.name)

    def schema(self, name):
        for catalog in self._catalogs.values():
            if name in catalog.tools:
                return copy.deepcopy(catalog.tools[name].input_schema)
        return None

    async def registered_server(self, name):
        slug, separator, _ = name.partition("__")
        if not separator:
            return None
        return next((s for s in await self.repository.list() if s.slug == slug), None)

    async def audit_target(self, name):
        server = await self.registered_server(name)
        catalog = self._catalogs.get(server.id) if server else None
        # Unrecognized caller strings can contain secrets/PII. Persist only a
        # previously discovered tool name; cold valid names bind before dispatch.
        known = catalog is not None and name in catalog.originals
        return {"server_id": server.id if server else None,
                "server_slug": server.slug if server else None,
                "gateway_tool": name if known else "<unresolved>",
                "upstream_tool": catalog.originals[name] if known else None}

    async def call_tool(self, name, arguments, *, before_dispatch=None):
        attempted = False
        server = None
        try:
            server = await self.registered_server(name)
            if server is None:
                raise GatewayError("UNKNOWN_TOOL")
            if not server.enabled:
                raise GatewayError("UPSTREAM_DISABLED")
            catalog = self._catalogs.get(server.id)
            if not catalog or catalog.registration != server:
                await self.refresh(server)
                catalog = self._catalogs.get(server.id)
            if not catalog or catalog.registration != server or not catalog.available:
                raise GatewayError("UPSTREAM_UNAVAILABLE")
            if name not in catalog.originals:
                raise GatewayError("UNKNOWN_TOOL")
            if before_dispatch is not None:
                await before_dispatch(server, catalog.originals[name])
            try:
                validator(catalog.tools[name].input_schema).validate(arguments)
            except Exception:
                raise GatewayError("VALIDATION_ERROR") from None
            # Catch disable/edit/remove while a refresh was awaiting its upstream.
            if await self.repository.get(server.id) != server:
                raise GatewayError("UPSTREAM_CHANGED")

            async def still_current():
                return await self.repository.get(server.id) == server

            result = await self.upstream.call(server, catalog.originals[name], arguments,
                                             still_current=still_current)
            attempted = True
            if not await still_current():
                raise GatewayError("UPSTREAM_CHANGED", attempted=True)
            if not isinstance(result, CallToolResult):
                raise GatewayError("UPSTREAM_INVALID_RESPONSE", attempted=True)
            if result.is_error:
                # A remote error can contain secrets/PII or claim false certainty.
                raise GatewayError("UPSTREAM_TOOL_ERROR", attempted=True)
            await self._safe(result.model_dump(mode="json"))
            output_schema = catalog.tools[name].output_schema
            if output_schema is not None:
                validator(output_schema).validate(result.structured_content)
            await self.repository.observe(server, Observation("connected"))
            return CallToolResult(content=copy.deepcopy(result.content),
                                  structured_content=copy.deepcopy(result.structured_content), is_error=False)
        except Exception as error:
            failure = error if isinstance(error, GatewayError) else GatewayError("UPSTREAM_INVALID_RESPONSE", attempted=attempted)
            if attempted and not failure.attempted:
                failure = GatewayError(failure.code, attempted=True)
            if server and failure.code.startswith("UPSTREAM_") and failure.code not in {
                "UPSTREAM_DISABLED", "UPSTREAM_CHANGED", "UPSTREAM_TOOL_ERROR"
            }:
                if await self.repository.observe(server, Observation("unreachable", failure.code)):
                    catalog = self._catalogs.get(server.id)
                    if catalog:
                        catalog.available = False
            return failure.result()
