"""SDK-generated /mcp application. Offline core: no identity or authorization yet."""

from mcp.server.lowlevel import Server
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ListToolsResult

from .core import Gateway
from .repository import MemoryRepository


def create_server(gateway):
    async def list_tools(ctx, params):
        return ListToolsResult(tools=await gateway.list_tools())

    async def call_tool(ctx, params):
        # Do not forward caller _meta, headers, tokens or identity to upstreams.
        return await gateway.call_tool(params.name, params.arguments or {})

    return Server("Urumi Gateway", version="0.0.1", on_list_tools=list_tools,
                  on_call_tool=call_tool, get_tool_input_schema=gateway.schema)


def create_app(gateway=None):
    gateway = gateway or Gateway(MemoryRepository())
    return create_server(gateway).streamable_http_app(
        streamable_http_path="/mcp", json_response=True, stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"], allowed_origins=[]),
    )
