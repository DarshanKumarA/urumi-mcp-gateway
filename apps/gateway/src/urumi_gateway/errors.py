"""Fixed public errors: never stringify upstream exceptions or rejected payloads."""

from mcp.types import CallToolResult, TextContent


class GatewayError(Exception):
    def __init__(self, code, *, attempted=False):
        self.code = code
        self.attempted = attempted
        super().__init__(code)

    def result(self):
        message = self.code
        if self.attempted:
            message += "; write_outcome=unknown; retry_safe=false"
        return CallToolResult(is_error=True, content=[TextContent(type="text", text=message)])
