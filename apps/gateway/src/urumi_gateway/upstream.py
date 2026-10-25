"""Official Streamable HTTP client; operation-scoped sessions, no call replay."""

import asyncio
import logging
from contextlib import AsyncExitStack, asynccontextmanager

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError

from .errors import GatewayError
from .models import Timeouts


class _Discard(logging.Filter):
    def filter(self, record):
        return False


def suppress_wire_logging():
    # These SDK/HTTP loggers can include untrusted bodies, URLs or errors, even at
    # WARNING. No raw wire diagnostics in this backend. Safe health codes are kept.
    names = set(logging.Logger.manager.loggerDict) | {"httpx2", "httpcore2", "mcp"}
    for name in names:
        if not any(name == p or name.startswith(p + ".") for p in ("httpx2", "httpcore2", "mcp")):
            continue
        logger = logging.getLogger(name)
        if not any(isinstance(f, _Discard) for f in logger.filters):
            logger.addFilter(_Discard())


class UpstreamClient:
    def __init__(self, *, timeouts=None, transport_factory=None):
        self.timeouts = timeouts or Timeouts()
        self.transport_factory = transport_factory
        suppress_wire_logging()

    @asynccontextmanager
    async def _connection(self, server):
        async def reject_redirect(response):
            # SDK follows same-origin redirects regardless of follow_redirects.
            # Reject before its redirect/log path; credentials stay at this URL.
            if 300 <= response.status_code < 400:
                raise GatewayError("UPSTREAM_REDIRECT")

        transport = self.transport_factory(server) if self.transport_factory else None
        async with httpx2.AsyncClient(
            transport=transport, headers=server.credential.headers() if server.credential else {},
            timeout=max(self.timeouts.discovery, self.timeouts.call), trust_env=False,
            follow_redirects=False, event_hooks={"response": [reject_redirect]},
        ) as http:
            async with Client(streamable_http_client(server.url, http_client=http),
                              cache=None, read_timeout_seconds=max(self.timeouts.discovery, self.timeouts.call),
                              mode="auto") as client:
                yield client

    async def _tools(self, client):
        tools, seen = [], set()
        cursor = None
        for _ in range(20):
            page = await client.list_tools(cursor=cursor, cache_mode="bypass")
            tools.extend(page.tools)
            if len(tools) > 500:
                raise GatewayError("UPSTREAM_INVALID_RESPONSE")
            cursor = page.next_cursor
            if cursor is None:
                return tools
            if cursor in seen:
                break
            seen.add(cursor)
        raise GatewayError("UPSTREAM_INVALID_RESPONSE")

    @staticmethod
    def _error(error, attempted=False):
        # ExceptionGroup can wrap transport failures. Only inspect types/codes.
        if isinstance(error, BaseExceptionGroup):
            errors = [UpstreamClient._error(e, attempted) for e in error.exceptions]
            for mapped in errors:
                if mapped.code != "UPSTREAM_UNAVAILABLE":
                    return mapped
        if isinstance(error, GatewayError):
            return GatewayError(error.code, attempted=attempted)
        if isinstance(error, (TimeoutError, httpx2.TimeoutException)):
            return GatewayError("UPSTREAM_TIMEOUT", attempted=attempted)
        if isinstance(error, MCPError) and error.code == -32001:
            return GatewayError("UPSTREAM_TIMEOUT", attempted=attempted)
        return GatewayError("UPSTREAM_UNAVAILABLE", attempted=attempted)

    async def discover(self, server):
        try:
            async with asyncio.timeout(self.timeouts.discovery):
                async with self._connection(server) as client:
                    return await self._tools(client)
        except Exception as error:
            raise self._error(error) from None

    async def call(self, server, original_name, arguments, *, still_current=None):
        attempted = False
        try:
            # Total includes connect/list and call; sessions always exit in the
            # task that entered them, including cancellation and timeouts.
            async with asyncio.timeout(self.timeouts.discovery + self.timeouts.call):
                async with AsyncExitStack() as stack:
                    async with asyncio.timeout(self.timeouts.discovery):
                        client = await stack.enter_async_context(self._connection(server))
                        tools = await self._tools(client)
                    if original_name not in {t.name for t in tools}:
                        raise GatewayError("UNKNOWN_TOOL")
                    if still_current is not None and not await still_current():
                        raise GatewayError("UPSTREAM_CHANGED")
                    async with asyncio.timeout(self.timeouts.call):
                        attempted = True
                        # Official session API avoids Client.call_tool's automatic
                        # HeaderMismatch retry and input-required continuation loop.
                        return await client.session.call_tool(original_name, arguments,
                                                              read_timeout_seconds=self.timeouts.call)
        except Exception as error:
            raise self._error(error, attempted) from None
