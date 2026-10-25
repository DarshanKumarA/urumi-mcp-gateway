"""Per-HTTP-request Bearer verification before the official MCP transport."""
from dataclasses import dataclass
import re
from uuid import UUID

from starlette.responses import JSONResponse

from .identity import IdentityError, username


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    username: str
    role: str
    api_key_id: UUID | None
    source: str = "api_key"

    def __post_init__(self):
        username(self.username)
        if (not isinstance(self.user_id, UUID) or self.role not in {"admin", "member"}
                or self.source not in {"api_key", "session"}
                or (self.source == "api_key" and not isinstance(self.api_key_id, UUID))
                or (self.source == "session" and self.api_key_id is not None)):
            raise ValueError("INVALID_PRINCIPAL")


def request_principal(ctx):
    principal = ctx.request.scope.get("state", {}).get("urumi_principal") if ctx.request else None
    if not isinstance(principal, Principal):
        raise IdentityError()
    return principal


class MCPAuthentication:
    def __init__(self, app, *, identity):
        self.app, self.identity = app, identity

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        try:
            headers = [v for k, v in scope.get("headers", []) if k.lower() == b"authorization"]
            if len(headers) != 1:
                raise IdentityError()
            match = re.fullmatch(rb"(?i:Bearer) (urumi_key_[A-Za-z0-9_-]{43})", headers[0])
            if not match:
                raise IdentityError()
            verified = await self.identity.verify_key(match[1].decode("ascii"))
            user = verified["user"]
            principal = Principal(user["id"], user["username"], user["role"], verified["key_id"])
        except IdentityError:
            return await JSONResponse({"error": "UNAUTHENTICATED"}, status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="urumi-gateway"', "Cache-Control": "no-store"})(scope, receive, send)
        except Exception:
            return await JSONResponse({"error": "AUTH_UNAVAILABLE"}, status_code=503,
                headers={"Cache-Control": "no-store"})(scope, receive, send)

        # Copy rather than mutate potentially shared lifespan/request state. The SDK
        # carries this exact HTTP Request into modern and legacy handler contexts.
        child = dict(scope, state={**scope.get("state", {}), "urumi_principal": principal})
        # Neither SDK diagnostics nor upstream adapters need the caller's raw key.
        child["headers"] = [(k, v) for k, v in scope.get("headers", []) if k.lower() != b"authorization"]
        await self.app(child, receive, send)
