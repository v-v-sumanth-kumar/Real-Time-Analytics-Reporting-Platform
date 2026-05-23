from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase

AlertStatus = Literal["active", "triggered", "resolved", "muted"]
AlertOperator = Literal["gt", "lt", "gte", "lte"]


class NotificationChannels(BaseModel):
    in_app: bool = True
    email: bool = False
    webhook_url: str | None = None


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    event_name: str | None = None
    metric: str = "count"
    operator: AlertOperator = "gt"
    threshold: float = Field(gt=0)
    window_minutes: int = Field(default=10, ge=1, le=1440)
    notification_channels: NotificationChannels = Field(default_factory=NotificationChannels)


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    event_name: str | None = None
    threshold: float | None = Field(default=None, gt=0)
    window_minutes: int | None = Field(default=None, ge=1, le=1440)
    notification_channels: NotificationChannels | None = None
    status: AlertStatus | None = None


class AlertRuleResponse(ORMBase):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    event_name: str | None
    metric: str
    operator: str
    threshold: float
    window_minutes: int
    status: str
    muted_until: datetime | None
    notification_channels: dict[str, Any]
    last_triggered_at: datetime | None
    last_value: float | None
    created_at: datetime


class AlertMuteRequest(BaseModel):
    minutes: int = Field(default=60, ge=5, le=10080)


class AlertIncidentResponse(ORMBase):
    id: UUID
    alert_rule_id: UUID
    organization_id: UUID
    status: str
    triggered_value: float
    triggered_at: datetime
    resolved_at: datetime | None
    created_at: datetime


class NotificationResponse(ORMBase):
    id: UUID
    organization_id: UUID
    user_id: UUID | None
    type: str
    title: str
    message: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime
