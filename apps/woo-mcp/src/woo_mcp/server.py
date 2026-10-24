"""Official SDK ASGI scaffold: five Woo tools, no caller authentication yet."""

import logging
from contextlib import asynccontextmanager

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.tools import Tool
from mcp.server.mcpserver.utilities.func_metadata import FuncMetadata
from mcp.types import ToolAnnotations
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import ValidationError

from .config import Config, Credentials
from .models import (CreatedProduct, CreatePrice, CreateProductInput, CreateStatus,
                     CreateStockStatus, ProductName, GetOrderInput, ListOrdersInput, ListProductsInput, OrderCollection,
                     OrderDate, OrderDetail, OrderID, OrderStatus, Page, PageSize,
                     ProductCollection, Search, SKU, Status, StrictModel,
                     UpdateOrderStatusInput, UpdatedOrderStatus, WritableOrderStatus)
from .woocommerce import WooClient, WooError


class StrictArguments(FuncMetadata):
    """Bind strict flat input to the pinned SDK, without its JSON-string coercion."""

    input_model: type[StrictModel]

    def validate_arguments(self, arguments_to_validate):
        try:
            return self.input_model.model_validate(arguments_to_validate).model_dump()
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
            raise ToolError(str(error)) from None
        except Exception:
            # Keep SDK unexpected-error logging from exposing upstream/request details.
            raise ToolError("WOO_INTERNAL_ERROR") from None

    async def get_order(ctx: Context[WooClient], order_id: OrderID) -> OrderDetail:
        """Get operational order details without customer contact or address fields."""
        return await tool_call(ctx, GetOrderInput, "get_order", order_id=order_id)

    async def list_orders(ctx: Context[WooClient], page: Page = 1, per_page: PageSize = 20,
                          status: OrderStatus | None = None, date: OrderDate | None = None) -> OrderCollection:
        """List one page of orders; today uses the store timezone. Reuse the returned date for later pages."""
        return await tool_call(ctx, ListOrdersInput, "list_orders", page=page,
                                per_page=per_page, status=status, date=date)

    async def create_product(ctx: Context[WooClient], name: ProductName, price: CreatePrice,
                             sku: SKU | None = None, status: CreateStatus = "publish",
                             stock_status: CreateStockStatus = "instock") -> CreatedProduct:
        """Create one simple product. Never automatically retry an unknown write outcome."""
        return await tool_call(ctx, CreateProductInput, "create_product", name=name, price=price,
                               sku=sku, status=status, stock_status=stock_status)

    async def update_order_status(ctx: Context[WooClient], order_id: OrderID,
                                  status: WritableOrderStatus, expected_status: OrderStatus) -> UpdatedOrderStatus:
        """Guard observed status, then at most one PUT. Not atomic; hooks may run. Never retry unknown writes."""
        return await tool_call(ctx, UpdateOrderStatusInput, "update_order_status", order_id=order_id,
                               status=status, expected_status=expected_status)

    async def tool_call(ctx, model, method, **values):
        try:
            query = model.model_validate(values)
            return await getattr(ctx.request_context.lifespan_context, method)(query)
        except ValidationError:
            raise ToolError("VALIDATION_ERROR") from None
        except WooError as error:
            raise ToolError(str(error)) from None
        except Exception:
            raise ToolError("WOO_INTERNAL_ERROR") from None

    tools = []
    for function, model in ((list_products, ListProductsInput), (get_order, GetOrderInput),
                            (list_orders, ListOrdersInput), (create_product, CreateProductInput),
                            (update_order_status, UpdateOrderStatusInput)):
        read_only = function in (list_products, get_order, list_orders)
        tool = Tool.from_function(function, structured_output=True,
                                  annotations=ToolAnnotations(read_only_hint=read_only,
                                                              destructive_hint=not read_only,
                                                              idempotent_hint=read_only))
        tool.fn_metadata = StrictArguments(**tool.fn_metadata.model_dump(), input_model=model)
        tool.parameters = model.model_json_schema()
        tools.append(tool)
    return MCPServer("Urumi WooCommerce", tools=tools, lifespan=lifespan, subscriptions=False)


def create_app():
    """ASGI factory; reads credentials only when application lifespan starts."""
    config = Config.from_environment()
    return create_server(config).streamable_http_app(
        streamable_http_path="/mcp", json_response=True, stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                                     allowed_hosts=list(config.allowed_hosts),
                                                     allowed_origins=[]))
