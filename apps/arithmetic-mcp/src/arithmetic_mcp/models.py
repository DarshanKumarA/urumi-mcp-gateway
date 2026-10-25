"""Finite, bounded decimal strings. No float coercion or expression evaluation."""
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Amount = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=26,
    pattern=r"^-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,6})?$")]
Currency = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=3,
    pattern=r"^[A-Z]{3}$")]


class Input(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    amounts: list[Amount] = Field(min_length=1, max_length=100)
    currency: Currency | None = None


class Result(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    count: int = Field(ge=1, le=100)
    total: str
    average: str
    minimum: str
    maximum: str
    currency: Currency | None = None
