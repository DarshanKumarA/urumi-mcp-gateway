"""Only the explicit policy keys and allowlisted structured fields."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

PolicyKey = Literal["cod", "dispatch", "cancellation"]


class Input(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    key: PolicyKey


class Result(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    key: PolicyKey
    title: str = Field(min_length=1, max_length=100)
    guidance: str = Field(min_length=1, max_length=500)
