"""Admin-only metadata listing; no audit mutation or payload-recovery API."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from .auth_api import admin


class AuditQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    page: int = Field(default=1, ge=1, le=100000)
    per_page: int = Field(default=20, ge=1, le=100)
    user_id: UUID | None = None
    server_slug: str | None = Field(default=None, min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_]*$")
    tool: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    outcome: Literal["started", "succeeded", "failed"] | None = None


def audit_router(repository):
    router = APIRouter(dependencies=[Depends(admin)])

    @router.get("/api/audits")
    async def listing(query: Annotated[AuditQuery, Query()]):
        return await repository.list_events(**query.model_dump())

    return router
