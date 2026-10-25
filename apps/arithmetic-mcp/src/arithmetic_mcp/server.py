"""Official SDK /mcp app; strict bounded inputs and no outbound business I/O."""
import os
import re
from mcp.server import MCPServer
from mcp.server.mcpserver.tools import Tool
from mcp.server.mcpserver.utilities.func_metadata import FuncMetadata
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import ValidationError
from .models import Input, Result
from .logic import execute


class StrictArguments(FuncMetadata):
    def validate_arguments(self, arguments_to_validate):
        try:
            return Input.model_validate(arguments_to_validate).model_dump()
        except ValidationError:
            # Pinned SDK adapter: reject coercion/extras without echoing input.
            raise ValidationError.from_exception_data("VALIDATION_ERROR", [{
                "type": "value_error", "loc": (), "input": None,
                "ctx": {"error": ValueError("VALIDATION_ERROR")},
            }], hide_input=True) from None


def allowed_hosts():
    raw = os.environ.get("MCP_ALLOWED_HOSTS", "127.0.0.1,127.0.0.1:8000,localhost,localhost:8000")
    hosts = raw.split(",")
    valid = re.compile(r"(?:localhost|127\.0\.0\.1|[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?)(?::[0-9]{1,5})?", re.ASCII)
    if (not 1 <= len(hosts) <= 20 or len(set(hosts)) != len(hosts)
            or any(not valid.fullmatch(h) or (":" in h and not 1 <= int(h.rsplit(":", 1)[1]) <= 65535) for h in hosts)):
        raise ValueError("INVALID_HOST_CONFIGURATION")
    return hosts


def create_server():
    async def sum_amounts(amounts: list[str], currency: str | None = None) -> Result:
        """Aggregate 1-100 amounts; exact sum/min/max, mean rounded half-even to 6 decimals."""
        return execute(Input(amounts=amounts, currency=currency))
    tool = Tool.from_function(sum_amounts, structured_output=True,
        annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                    idempotent_hint=True, open_world_hint=False))
    tool.fn_metadata = StrictArguments(**tool.fn_metadata.model_dump())
    tool.parameters = Input.model_json_schema()
    return MCPServer("Urumi Arithmetic", tools=[tool], subscriptions=False)


def create_app():
    return create_server().streamable_http_app(streamable_http_path="/mcp",
        json_response=True, stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts(), allowed_origins=[]))
