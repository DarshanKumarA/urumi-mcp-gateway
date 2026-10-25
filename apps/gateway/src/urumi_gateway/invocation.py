"""One attributed invocation path for external MCP and future session-derived chat."""
from datetime import datetime, timezone
import time

from .audit_repository import AuditUnavailable, ERROR_CODES
from .errors import GatewayError
from .mcp_auth import Principal


class InvocationService:
    def __init__(self, gateway, audits):
        self.gateway, self.audits = gateway, audits

    async def invoke_tool(self, principal, name, arguments):
        if not isinstance(principal, Principal):
            return GatewayError("UNAUTHENTICATED").result()
        start = time.monotonic()
        try:
            target = await self.gateway.audit_target(name)
            event_id = await self.audits.start(principal, target, datetime.now(timezone.utc))
        except Exception:
            # No discovery or upstream invocation has occurred through this path.
            return GatewayError("AUDIT_UNAVAILABLE").result()

        async def before_dispatch(server, original):
            if server.id != target["server_id"] or server.slug != target["server_slug"]:
                raise GatewayError("UPSTREAM_CHANGED")
            try:
                # Original tool is supplied by the authoritative core mapping,
                # never reconstructed from an exposed/truncated gateway name.
                await self.audits.bind_tool(event_id, name, original)
            except AuditUnavailable:
                raise GatewayError("AUDIT_UNAVAILABLE") from None

        try:
            result = await self.gateway.call_tool(name, arguments, before_dispatch=before_dispatch)
        except Exception:
            result = GatewayError("GATEWAY_FAILURE", attempted=True).result()
        # Cancellation/process death deliberately leaves the durable started row.
        code = None
        if result.is_error:
            message = getattr(result.content[0], "text", "") if result.content else ""
            candidate = message.partition(";")[0]
            code = candidate if candidate in ERROR_CODES else "GATEWAY_FAILURE"
        try:
            await self.audits.finish(event_id, "failed" if result.is_error else "succeeded", code,
                datetime.now(timezone.utc), max(0, int((time.monotonic() - start) * 1000)))
        except Exception:
            # The upstream may already have acted. Do not retry or claim rollback.
            return GatewayError("AUDIT_FINALIZATION_FAILED", attempted=True).result()
        return result
