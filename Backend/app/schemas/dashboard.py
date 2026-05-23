from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase

WidgetType = Literal["line", "bar", "pie", "kpi"]


class WidgetQuery(BaseModel):
    event_name: str | None = None
    metric: str = "count"
    group_by: str | None = None
    time_range: str = "24h"
    granularity: str = "1h"
    filters: dict[str, Any] = Field(default_factory=dict)


class WidgetCreate(BaseModel):
    type: WidgetType
    title: str = Field(min_length=1, max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)
    query: WidgetQuery | dict[str, Any] = Field(default_factory=dict)
    position: dict[str, Any] = Field(default_factory=dict)
    refresh_interval_sec: int = Field(default=30, ge=5, le=3600)


class WidgetUpdate(BaseModel):
    title: str | None = None
    config: dict[str, Any] | None = None
    query: dict[str, Any] | None = None
    position: dict[str, Any] | None = None
    refresh_interval_sec: int | None = Field(default=None, ge=5, le=3600)


class WidgetResponse(ORMBase):
    id: UUID
    dashboard_id: UUID
    organization_id: UUID
    type: str
    title: str
    config: dict[str, Any]
    query: dict[str, Any]
    position: dict[str, Any]
    refresh_interval_sec: int
    created_at: datetime


class DashboardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    layout: dict[str, Any] = Field(default_factory=dict)
    refresh_interval_sec: int = Field(default=30, ge=5, le=3600)


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    layout: dict[str, Any] | None = None
    refresh_interval_sec: int | None = Field(default=None, ge=5, le=3600)
    is_public: bool | None = None


class DashboardResponse(ORMBase):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    layout: dict[str, Any]
    is_public: bool
    refresh_interval_sec: int
    widgets: list[WidgetResponse] = []
    share_url: str | None = None
    created_at: datetime


class MetricDataPoint(BaseModel):
    label: str
    value: float
    timestamp: str | None = None


class WidgetMetricsResponse(BaseModel):
    widget_id: UUID
    type: str
    data: list[MetricDataPoint]
    total: float | None = None
