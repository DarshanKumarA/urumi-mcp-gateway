"""Official SDK ASGI scaffold: exactly one business tool, no caller auth yet."""

import logging
from contextlib import asynccontextmanager

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.tools import Tool
from mcp.server.mcpserver.utilities.func_metadata import FuncMetadata
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from .config import Config, Credentials
from .models import ListProductsInput, Page, PageSize, ProductCollection, Search, SKU, Status
from .woocommerce import WooClient, WooError


class ProductArguments(FuncMetadata):
    """Bind strict flat input to the pinned SDK, without its JSON-string coercion."""

    def validate_arguments(self, arguments_to_validate):
        try:
            return ListProductsInput.model_validate(arguments_to_validate).model_dump()
        except ValidationError:
            # SDK wraps argument ValidationError into ToolError; other exception
            # types here are crashes. Remove even rejected field names/values.
            raise ValidationError.from_exception_data("VALIDATION_ERROR", [{
                "type": "value_error", "loc": (), "input": None,
                "ctx": {"error": ValueError("VALIDATION_ERROR")},
            }], hide_input=True) from None


def create_server(config=None, *, client_factory=None):
    config = config or Config()

    @asynccontextmanager
    async def lifespan(server):
        # Signing debug can include secrets. Do not enable wire/debug logging.
        for name in ("oauthlib", "httpx", "httpcore"):
            logging.getLogger(name).setLevel(logging.WARNING)
        client = (client_factory() if client_factory else
                  WooClient(config, Credentials.from_directory(config.secret_directory)))
        async with client:
            yield client

    async def list_products(ctx: Context[WooClient], page: Page = 1, per_page: PageSize = 20,
                            search: Search | None = None, sku: SKU | None = None,
                            status: Status | None = None) -> ProductCollection:
        """List one page of store products. Use search or SKU, not both."""
        try:
            query = ListProductsInput(page=page, per_page=per_page, search=search, sku=sku, status=status)
            return await ctx.request_context.lifespan_context.list_products(query)
        except ValidationError:
            raise ToolError("VALIDATION_ERROR") from None
        except WooError as error:
            raise ToolError(error.code) from None
        except Exception:
            # Keep SDK unexpected-error logging from exposing upstream/request details.
            raise ToolError("WOO_INTERNAL_ERROR") from None

    tool = Tool.from_function(list_products, structured_output=True,
                              annotations=ToolAnnotations(read_only_hint=True,
                                                          destructive_hint=False,
                                                          idempotent_hint=True))
    tool.fn_metadata = ProductArguments(**tool.fn_metadata.model_dump())
    tool.parameters = ListProductsInput.model_json_schema()
    return MCPServer("Urumi WooCommerce", tools=[tool], lifespan=lifespan, subscriptions=False)


def create_app():
    """ASGI factory; reads credentials only when application lifespan starts."""
    return create_server().streamable_http_app(
        streamable_http_path="/mcp", json_response=True, stateless_http=True)
