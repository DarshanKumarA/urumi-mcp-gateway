"""Strict tool inputs and allowlisted structured outputs; no REST passthrough."""

from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

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
