import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

# TODO: PARTITION BY RANGE (occurred_at) when volume warrants monthly partitions


class Event(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_org_time", "organization_id", "occurred_at"),
        Index("idx_events_org_name_time", "organization_id", "event_name", "occurred_at"),
        Index(
            "idx_events_properties_gin",
            "properties",
            postgresql_using="gin",
            postgresql_ops={"properties": "jsonb_path_ops"},
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="api", nullable=False)
    ingest_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
