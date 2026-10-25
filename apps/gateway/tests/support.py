"""Offline official-SDK upstreams behind real ASGI transports; synthetic data only."""

import asyncio
import json
from contextlib import AsyncExitStack, asynccontextmanager

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.lowlevel import Server
from mcp.shared.exceptions import MCPError
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool, ToolAnnotations

from urumi_gateway.core import Gateway
from urumi_gateway.models import Credential, Timeouts, Upstream
from urumi_gateway.repository import MemoryRepository
from urumi_gateway.server import create_app
from urumi_gateway.upstream import UpstreamClient

SYNTHETIC = "synthetic-upstream-fixture-value-only"
SCHEMA = {"type": "object", "properties": {"value": {"type": "integer", "description": "Integer input"}},
          "required": ["value"], "additionalProperties": False}
OUTPUT = {"type": "object", "properties": {"value": {"type": "integer"}, "server": {"type": "string"}},
          "required": ["value", "server"], "additionalProperties": False}


class UpstreamFixture:
    def __init__(self, slug):
        self.slug = slug
        self.calls = []
        self.headers = []
        self.methods = []
        self.closed = 0
        self.list_count = 0
        self.cursors = []
        self.mode = "normal"
        self.discover_delay = 0
        self.call_delay = 0
        self.list_started = asyncio.Event()
        self.call_started = asyncio.Event()
        self.list_release = None
        self.tools = [Tool(name=name, description=f"Untrusted {name} description", input_schema=SCHEMA,
                           output_schema=OUTPUT, annotations=ToolAnnotations(read_only_hint=True))
                      for name in (["echo", "shared_name"] if slug == "server_a" else ["add", "shared_name"])]
        async def listing(ctx, params):
            self.list_count += 1
            cursor = params.cursor if params else None
            self.cursors.append(cursor)
            self.list_started.set()
            if self.list_release:
                await self.list_release.wait()
            await asyncio.sleep(self.discover_delay)
            if self.mode == "list_fail":
                raise MCPError(-32000, SYNTHETIC)
            if self.mode == "pagination":
                return ListToolsResult(tools=self.tools[1:] if cursor else self.tools[:1],
                                       next_cursor=None if cursor else "second")
            if self.mode == "cursor_loop":
                return ListToolsResult(tools=[], next_cursor="repeated")
            return ListToolsResult(tools=self.tools)

        async def call(ctx, params):
            self.calls.append((params.name, params.arguments))
            self.call_started.set()
            await asyncio.sleep(self.call_delay)
            if self.mode in {"protocol_error", "header_mismatch"}:
                raise MCPError(-32020 if self.mode == "header_mismatch" else -32000, SYNTHETIC)
            if self.mode == "tool_error":
                return CallToolResult(is_error=True, content=[TextContent(type="text", text=SYNTHETIC)])
            if self.mode == "malformed":
                return CallToolResult(content=[], structured_content={"private": SYNTHETIC})
            data = {"value": params.arguments["value"] + (1 if self.slug == "server_b" else 0),
                    "server": SYNTHETIC if self.mode == "echo_secret" else self.slug}
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(data))], structured_content=data)

        self.app = Server(slug, on_list_tools=listing, on_call_tool=call,
                          get_tool_input_schema=lambda name: SCHEMA).streamable_http_app(
                              json_response=True, stateless_http=True)

    def transport(self):
        fixture = self
        class Transport(httpx2.AsyncBaseTransport):
            def __init__(self):
                self.inner = httpx2.ASGITransport(app=fixture.app)

            async def handle_async_request(self, request):
                fixture.headers.append(dict(request.headers))
                if request.method == "POST":
                    method = json.loads(request.content).get("method")
                    fixture.methods.append(method)
                    if fixture.mode == "legacy" and method == "server/discover":
                        return httpx2.Response(404)
                    if fixture.mode == "lost_call" and method == "tools/call":
                        raise httpx2.ReadError(SYNTHETIC, request=request)
                    if fixture.mode == "bad_json" and method == "tools/list":
                        return httpx2.Response(200, text="{broken", headers={"Content-Type": "application/json"})
                if fixture.mode == "dead":
                    raise httpx2.ConnectError(SYNTHETIC, request=request)
                if fixture.mode == "redirect":
                    return httpx2.Response(307, headers={"Location": "http://127.0.0.1:9001/other"})
                return await self.inner.handle_async_request(request)

            async def aclose(self):
                fixture.closed += 1
                await self.inner.aclose()
        return Transport()


@asynccontextmanager
async def setup(mode="auto", *, discovery=1.0, call=1.0, incoming_headers=None):
    a, b = UpstreamFixture("server_a"), UpstreamFixture("server_b")
    repo = MemoryRepository()
    sa = Upstream("server_a", "Server A", "http://127.0.0.1:9001/mcp",
                  credential=Credential("bearer", SYNTHETIC))
    sb = Upstream("server_b", "Server B", "http://127.0.0.1:9002/mcp")
    await repo.add(sa)
    await repo.add(sb)
    fixtures = {sa.id: a, sb.id: b}
    upstream = UpstreamClient(timeouts=Timeouts(discovery, call),
                              transport_factory=lambda s: fixtures[s.id].transport())
    gateway = Gateway(repo, upstream)
    app = create_app(gateway)
    async with AsyncExitStack() as stack:
        for application in (a.app, b.app, app):
            await stack.enter_async_context(application.router.lifespan_context(application))
        http = await stack.enter_async_context(httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), trust_env=False, headers=incoming_headers))
        client = await stack.enter_async_context(Client(
            streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http),
            mode=mode, cache=None))
        yield client, gateway, repo, sa, sb, a, b
