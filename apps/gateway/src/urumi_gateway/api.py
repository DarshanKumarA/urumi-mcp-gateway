"""Single REST/MCP backend. REST sessions and per-request MCP identity with durable invocation audits."""

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID
from urllib.parse import urlsplit
import os

from fastapi import FastAPI, Response, APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .identity import IdentityService, AuthConfig, IdentityError
from .identity_repository import IdentityRepository
from .auth_api import identity_router, admin, same_origin
from .audit_repository import AuditRepository, AuditUnavailable
from .audit_api import audit_router
from .invocation import InvocationService
from .chat import ChatService, chat_router
from .core import Gateway
from .database import SQLRepository, RepositoryUnavailable, make_engine
from .errors import GatewayError
from .management import Management, CreateServer, EditServer, ServerView
from .server import create_app as mcp_app


def create_app(repository, *, upstream=None, seed=False, auth_config=None, identity=None, provider=None, max_tool_rounds=5):
    gateway = Gateway(repository, upstream)
    service = Management(gateway)
    identity = identity or IdentityService(IdentityRepository(repository.engine), auth_config)
    audits = AuditRepository(repository.engine)
    invocations = InvocationService(gateway, audits)
    mcp = mcp_app(gateway, identity=identity, invocations=invocations)

    @asynccontextmanager
    async def lifespan(app):
        if seed:
            await repository.seed_woocommerce()
        # Starlette does not automatically run mounted app lifespans.
        async with mcp.router.lifespan_context(mcp):
            yield

    app = FastAPI(title="Urumi management", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.audits = audits
    app.state.invocations = invocations
    app.state.identity = identity
    app.state.gateway = gateway
    app.state.management = service
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[urlsplit(identity.config.origin).hostname])

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(AuditUnavailable)
    async def audit_unavailable(request, error):
        return JSONResponse({"error": "AUDIT_UNAVAILABLE"}, status_code=503)

    @app.exception_handler(IdentityError)
    async def authentication_failed(request, error):
        return JSONResponse({"error": error.code}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, error):
        # FastAPI defaults include rejected input, potentially a credential.
        return JSONResponse({"error": "VALIDATION_ERROR"}, status_code=422)

    @app.exception_handler(ValueError)
    async def invalid_value(request, error):
        conflict = error.args == ("DUPLICATE_REGISTRATION",) or error.args == ("REGISTRY_CONFLICT",)
        return JSONResponse({"error": "REGISTRY_CONFLICT" if conflict else "VALIDATION_ERROR"},
                            status_code=409 if conflict else 422)

    @app.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse({"error": "NOT_FOUND"}, status_code=404)

    @app.exception_handler(RepositoryUnavailable)
    async def unavailable(request, error):
        return JSONResponse({"error": "REGISTRY_UNAVAILABLE"}, status_code=503)

    @app.exception_handler(GatewayError)
    async def unsafe_metadata(request, error):
        return JSONResponse({"error": "UNSAFE_UPSTREAM_METADATA"}, status_code=502)

    management = APIRouter(dependencies=[Depends(admin), Depends(same_origin)])

    @management.get("/api/servers", response_model=list[ServerView])
    async def listing():
        return await service.list()

    @management.post("/api/servers", response_model=ServerView, status_code=201)
    async def create(body: CreateServer):
        return await service.create(body)

    @management.get("/api/servers/{server_id}", response_model=ServerView)
    async def detail(server_id: UUID):
        return await service.detail(server_id)

    @management.patch("/api/servers/{server_id}", response_model=ServerView)
    async def edit(server_id: UUID, body: EditServer):
        return await service.edit(server_id, body)

    @management.delete("/api/servers/{server_id}", status_code=204)
    async def remove(server_id: UUID):
        await service.remove(server_id)
        return Response(status_code=204)

    @management.post("/api/servers/{server_id}/enable", response_model=ServerView)
    async def enable(server_id: UUID):
        return await service.edit(server_id, EditServer(enabled=True))

    @management.post("/api/servers/{server_id}/disable", response_model=ServerView)
    async def disable(server_id: UUID):
        return await service.edit(server_id, EditServer(enabled=False))

    @management.post("/api/servers/{server_id}/refresh", response_model=ServerView)
    async def refresh(server_id: UUID):
        return await service.refresh(server_id)

    app.state.chat = ChatService(gateway, invocations, provider, max_tool_rounds)
    app.include_router(chat_router(app.state.chat, gateway))
    app.include_router(audit_router(audits))
    app.include_router(identity_router(identity))
    app.include_router(management)

    # Mount last at root: SDK retains its exact /mcp path and transport middleware.
    app.mount("/", mcp)
    return app


def create_production_app():
    """Explicit PostgreSQL factory; never falls back to memory or creates schema."""
    try:
        url = Path(os.environ["URUMI_DATABASE_URL_FILE"]).read_text(encoding="utf-8").strip()
        engine = make_engine(url)
    except Exception:
        raise RuntimeError("DATABASE_CONFIGURATION_INVALID") from None
    try:
        environment = os.environ.get("URUMI_ENVIRONMENT", "production")
        if environment not in {"local", "production"}:
            raise ValueError("AUTH_CONFIGURATION_INVALID")
        secure = os.environ.get("URUMI_COOKIE_SECURE", "true")
        if secure not in {"true", "false"}:
            raise ValueError("AUTH_CONFIGURATION_INVALID")
        config = AuthConfig(origin=os.environ["URUMI_BROWSER_ORIGIN"],
            secure_cookie=secure == "true", production=environment == "production",
            session_seconds=int(os.environ.get("URUMI_SESSION_SECONDS", "28800")),
            invitation_seconds=int(os.environ.get("URUMI_INVITATION_SECONDS", "86400")))
        from .provider import from_environment
        provider = from_environment()
        app = create_app(SQLRepository(engine), seed=True, auth_config=config, provider=provider,
                         max_tool_rounds=int(os.environ.get("URUMI_MAX_TOOL_ROUNDS", "5")))
    except Exception:
        engine.dispose()
        raise RuntimeError("AUTH_CONFIGURATION_INVALID") from None
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        try:
            async with original(application):
                yield
        finally:
            try:
                if provider is not None:
                    await provider.close()
            finally:
                engine.dispose()
    app.router.lifespan_context = lifespan
    return app
