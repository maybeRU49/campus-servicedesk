"""Validated request bodies, independent of HTTP handlers and SQL."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TicketStatus = Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]


class RequestBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class TicketCreate(RequestBody):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5, max_length=2000)
    category: Literal["Hardware", "Software", "Network", "Access", "Other"]
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    department_id: int | None = Field(default=None, gt=0)
    asset_id: int | None = Field(default=None, gt=0)


class TicketStatusUpdate(RequestBody):
    new_status: TicketStatus


class TicketAssignmentCreate(RequestBody):
    technician_id: int = Field(gt=0)


class TicketCommentCreate(RequestBody):
    comment_text: str = Field(min_length=2, max_length=1000)
