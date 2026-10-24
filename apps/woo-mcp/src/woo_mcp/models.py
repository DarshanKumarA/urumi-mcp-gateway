"""Strict tool inputs and allowlisted structured outputs; no REST passthrough."""

from datetime import date as CalendarDate
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Status = Literal["publish", "draft", "pending", "private"]
Page = Annotated[int, Field(strict=True, ge=1)]
PageSize = Annotated[int, Field(strict=True, ge=1, le=50)]
Search = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)]
SKU = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=64)]
Money = Annotated[str, Field(max_length=24, pattern=r"^(?:[0-9]+(?:\.[0-9]+)?)?$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class ListProductsInput(StrictModel):
    page: Page = 1
    per_page: PageSize = 20
    search: Search | None = None
    sku: SKU | None = None
    status: Status | None = None

    @model_validator(mode="after")
    def filters(self):
        if self.search is not None and self.sku is not None:
            raise ValueError("Use search or sku, not both.")
        return self


class Product(StrictModel):
    id: Annotated[int, Field(gt=0)]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    sku: Annotated[str, Field(max_length=256)]
    type: Literal["simple", "grouped", "external", "variable"]
    price: Money
    regular_price: Money
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    status: Status
    stock_status: Literal["instock", "outofstock", "onbackorder"]
    permalink: Annotated[str, Field(max_length=2048)]

    @field_validator("permalink")
    @classmethod
    def public_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Expected a public product URL.")
        return value


class ProductCollection(StrictModel):
    items: list[Product]
    page: Page
    per_page: PageSize
    total: Annotated[int, Field(ge=0)]
    total_pages: Annotated[int, Field(ge=0)]
    has_more: bool
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


ProductName = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)]
CreatePrice = Annotated[str, Field(strict=True, pattern=r"^[0-9]+(?:\.[0-9]{1,2})?$",
                                   description="Nonnegative decimal string, at most two fractional digits; maximum 999999999.99.")]
CreateStatus = Literal["publish", "draft"]
CreateStockStatus = Literal["instock", "outofstock"]


class CreateProductInput(StrictModel):
    name: ProductName
    price: CreatePrice
    sku: SKU | None = None
    status: CreateStatus = "publish"
    stock_status: CreateStockStatus = "instock"

    @field_validator("price")
    @classmethod
    def price_limit(cls, value):
        if Decimal(value) > Decimal("999999999.99"):
            raise ValueError("Price exceeds the allowed maximum.")
        return value


class CreatedProduct(StrictModel):
    product: Product
    created: Literal[True] = True


OrderID = Annotated[int, Field(strict=True, gt=0)]
OrderStatus = Literal["pending", "processing", "on-hold", "completed", "cancelled", "refunded", "failed"]
OrderDate = Annotated[str, Field(pattern=r"^(today|[0-9]{4}-[0-9]{2}-[0-9]{2})$")]
OrderMoney = Annotated[str, Field(max_length=40, pattern=r"^[0-9]+(?:\.[0-9]+)?$")]


class GetOrderInput(StrictModel):
    order_id: OrderID


class ListOrdersInput(StrictModel):
    page: Page = 1
    per_page: PageSize = 20
    status: OrderStatus | None = None
    date: OrderDate | None = None

    @field_validator("date")
    @classmethod
    def valid_date(cls, value):
        if value is not None and value != "today":
            CalendarDate.fromisoformat(value)
        return value


class OrderSummary(StrictModel):
    id: OrderID
    status: OrderStatus
    created_at: AwareDatetime
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    total: OrderMoney
    payment_method: Annotated[str, Field(max_length=100)]


class OrderLine(StrictModel):
    product_id: Annotated[int, Field(ge=0)]
    variation_id: Annotated[int, Field(gt=0)] | None
    name: Annotated[str, Field(max_length=200)]
    sku: Annotated[str, Field(max_length=256)] | None
    quantity: Annotated[int, Field(gt=0)]
    unit_price: OrderMoney
    subtotal: OrderMoney
    total: OrderMoney


class ShippingLine(StrictModel):
    method_id: Annotated[str, Field(max_length=100)]
    method_title: Annotated[str, Field(max_length=200)]
    total: OrderMoney


class OrderDetail(OrderSummary):
    line_items: list[OrderLine]
    shipping_lines: list[ShippingLine]
    shipping_total: OrderMoney
    tax_total: OrderMoney


class OrderDateWindow(StrictModel):
    date: str
    timezone: str
    start_inclusive: AwareDatetime
    end_exclusive: AwareDatetime


class OrderCollection(StrictModel):
    items: list[OrderSummary]
    page: Page
    per_page: PageSize
    total: Annotated[int, Field(ge=0)]
    total_pages: Annotated[int, Field(ge=0)]
    has_more: bool
    date_window: OrderDateWindow | None
