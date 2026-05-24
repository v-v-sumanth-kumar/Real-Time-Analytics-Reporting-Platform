from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EventProperties(BaseModel):
    model_config = {"extra": "allow"}


class EventCreate(BaseModel):
    event_name: str = Field(min_length=1, max_length=128)
    occurred_at: datetime | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = Field(default=None, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)

    @field_validator("event_name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")


class EventBatchCreate(BaseModel):
    events: list[EventCreate] = Field(min_length=1, max_length=1000)


class EventIngestResponse(BaseModel):
    accepted: int
    ingest_id: UUID | None = None


class EventResponse(BaseModel):
    id: UUID
    event_name: str
    occurred_at: datetime
    received_at: datetime
    properties: dict[str, Any]
    user_id: str | None = None
    session_id: str | None = None
    source: str
