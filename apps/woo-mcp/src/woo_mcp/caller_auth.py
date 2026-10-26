"""Gateway service credential, separate from Woo REST and end-user credentials."""
import hmac
import os
from pathlib import Path
import re

from starlette.responses import JSONResponse


class CallerAuthentication:
    """Every HTTP request is checked; no sessions or bearer validity cache."""

    def __init__(self, app):
        self.app = app
        try:
            with Path(os.environ["WOO_MCP_AUTH_TOKEN_FILE"]).open("rb") as stream:
                token = stream.read(258).removesuffix(b"\n")
            if not re.fullmatch(rb"[A-Za-z0-9_-]{32,256}", token):
                raise ValueError()
            self._expected = b"Bearer " + token
        except Exception:
            raise ValueError("CALLER_AUTH_CONFIGURATION_INVALID") from None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = scope.get("headers", [])
        supplied = [v for k, v in headers if k.lower() == b"authorization"]
        if len(supplied) != 1 or not hmac.compare_digest(supplied[0], self._expected):
            return await JSONResponse({"error": "UNAUTHORIZED"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"})(scope, receive, send)
        # The SDK and Woo client never receive this service credential.
        scope = dict(scope, headers=[(k, v) for k, v in headers if k.lower() != b"authorization"])
        return await self.app(scope, receive, send)
