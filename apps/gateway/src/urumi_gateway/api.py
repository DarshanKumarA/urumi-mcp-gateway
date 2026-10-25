"""Single REST/MCP backend. NOT YET AUTHORIZED: loopback development only."""

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID
import os

from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .core import Gateway
from .database import SQLRepository, RepositoryUnavailable, make_engine
from .errors import GatewayError
from .management import Management, CreateServer, EditServer, ServerView
from .server import create_app as mcp_app


def create_app(repository, *, upstream=None, seed=False):
    gateway = Gateway(repository, upstream)
    service = Management(gateway)
    mcp = mcp_app(gateway)

    @asynccontextmanager
    async def lifespan(app):
        if seed:
            await repository.seed_woocommerce()
        # Starlette does not automatically run mounted app lifespans.
        async with mcp.router.lifespan_context(mcp):
            yield

    app = FastAPI(title="Urumi management (NOT YET AUTHORIZED)", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.gateway = gateway
    app.state.management = service
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

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

    @app.get("/api/servers", response_model=list[ServerView])
    async def listing():
        return await service.list()

    @app.post("/api/servers", response_model=ServerView, status_code=201)
    async def create(body: CreateServer):
        return await service.create(body)

    @app.get("/api/servers/{server_id}", response_model=ServerView)
    async def detail(server_id: UUID):
        return await service.detail(server_id)

    @app.patch("/api/servers/{server_id}", response_model=ServerView)
    async def edit(server_id: UUID, body: EditServer):
        return await service.edit(server_id, body)

    @app.delete("/api/servers/{server_id}", status_code=204)
    async def remove(server_id: UUID):
        await service.remove(server_id)
        return Response(status_code=204)

    @app.post("/api/servers/{server_id}/enable", response_model=ServerView)
    async def enable(server_id: UUID):
        return await service.edit(server_id, EditServer(enabled=True))

    @app.post("/api/servers/{server_id}/disable", response_model=ServerView)
    async def disable(server_id: UUID):
        return await service.edit(server_id, EditServer(enabled=False))

    @app.post("/api/servers/{server_id}/refresh", response_model=ServerView)
    async def refresh(server_id: UUID):
        return await service.refresh(server_id)

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
    app = create_app(SQLRepository(engine), seed=True)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        try:
            async with original(application):
                yield
        finally:
            engine.dispose()
    app.router.lifespan_context = lifespan
    return app
