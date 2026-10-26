"""SDK-generated /mcp application. Authenticated transport with a shared audited invocation path."""

from mcp.server.lowlevel import Server
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ListToolsResult

from .mcp_auth import MCPAuthentication, request_principal


def create_server(gateway, invocations):
    async def list_tools(ctx, params):
        request_principal(ctx)
        return ListToolsResult(tools=await gateway.list_tools())

    async def call_tool(ctx, params):
        # Do not forward caller _meta, headers, tokens or identity to upstreams.
        return await invocations.invoke_tool(request_principal(ctx), params.name, params.arguments or {})

    return Server("Urumi Gateway", version="0.0.1", on_list_tools=list_tools,
                  on_call_tool=call_tool, get_tool_input_schema=gateway.schema)


def create_app(gateway, *, identity, invocations, allowed_hosts=None):
    app = create_server(gateway, invocations).streamable_http_app(
        streamable_http_path="/mcp", json_response=True, stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts or ["127.0.0.1:*", "localhost:*", "[::1]:*"], allowed_origins=[]),
    )
    app.add_middleware(MCPAuthentication, identity=identity)
    return app
