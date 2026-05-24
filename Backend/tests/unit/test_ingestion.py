from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.schemas.event import EventCreate
from app.services.ingestion_service import IngestionService


def test_normalize_event_sets_utc_and_fields() -> None:
    org_id = uuid4()
    occurred = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    event = EventCreate(
        event_name="page_view",
        occurred_at=occurred,
        properties={"page": "/home"},
        user_id="user-1",
    )
    service = IngestionService(MagicMock(), MagicMock())
    payload = service.normalize_event(org_id, event, source="api")

    assert payload["organization_id"] == str(org_id)
    assert payload["event_name"] == "page_view"
    assert payload["properties"] == {"page": "/home"}
    assert payload["user_id"] == "user-1"
    assert payload["source"] == "api"
    assert "occurred_at" in payload
    assert "received_at" in payload


def test_parse_csv_maps_rows() -> None:
    csv_content = (
        "event_name,occurred_at,page,user_id\n"
        "page_view,2026-01-15T12:00:00+00:00,/pricing,u1\n"
    )
    rows = IngestionService.parse_csv(csv_content)

    assert len(rows) == 1
    assert rows[0]["event_name"] == "page_view"
    assert rows[0]["user_id"] == "u1"
    assert rows[0]["properties"]["page"] == "/pricing"
    assert rows[0]["source"] == "csv"


def test_parse_csv_skips_rows_without_event_name() -> None:
    csv_content = "occurred_at,page\n2026-01-15T12:00:00+00:00,/orphan\n"
    assert IngestionService.parse_csv(csv_content) == []
