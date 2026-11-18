"""Per-HTTP-request Bearer verification before the official MCP transport."""
from dataclasses import dataclass
import re
import asyncio
import json
import time
from datetime import datetime, timezone
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
    def __init__(self, app, *, identity, invocations=None):
        self.app, self.identity, self.invocations = app, identity, invocations

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        match = None
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
            if match and self.invocations is not None:
                try:
                    owner = await self.identity.rejected_key(match[1].decode("ascii"))
                    if owner:
                        await self.audit_rejection(owner, scope, receive)
                except Exception:
                    # Rejection is fail-closed even when durable auditing is unavailable.
                    return await JSONResponse({"error": "AUDIT_UNAVAILABLE"}, status_code=503,
                        headers={"Cache-Control": "no-store"})(scope, receive, send)
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

    async def audit_rejection(self, owner, scope, receive):
        start = time.monotonic()
        target = {"server_id": None, "server_slug": None,
                  "gateway_tool": "<authentication>", "upstream_tool": None}
        # Read only a small bounded request; never persist arguments/raw names or dispatch.
        if scope["method"] == "POST":
            try:
                async with asyncio.timeout(1):
                    body = bytearray()
                    while True:
                        part = await receive()
                        if part["type"] != "http.request": break
                        body.extend(part.get("body", b""))
                        if len(body) > 16384: break
                        if not part.get("more_body"):
                            request = json.loads(body)
                            if request.get("method") == "tools/call":
                                name = request.get("params", {}).get("name")
                                # Only previously discovered metadata is safe to record.
                                for catalog in self.invocations.gateway._catalogs.values():
                                    if isinstance(name, str) and name in catalog.originals:
                                        target = {"server_id": catalog.registration.id,
                                            "server_slug": catalog.registration.slug, "gateway_tool": name,
                                            "upstream_tool": catalog.originals[name]}
                                        break
                            break
            except (TimeoutError, ValueError, TypeError, AttributeError):
                pass
        user = owner["user"]
        principal = Principal(user["id"], user["username"], user["role"], owner["key_id"])
        now = datetime.now(timezone.utc)
        await self.invocations.audits.rejected(principal, target, now,
            max(0, int((time.monotonic() - start)*1000)))
