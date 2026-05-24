import json

import pytest
from httpx import AsyncClient

from app.services.ingestion_service import IngestionService
from tests.conftest import INTEGRATION_ENABLED, auth_headers

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not INTEGRATION_ENABLED, reason="Set TEST_DATABASE_URL to run integration tests")
async def test_ingest_event_enqueues_to_redis(
    client: AsyncClient,
    registered_user: dict,
    fake_redis,
) -> None:
    headers = auth_headers(registered_user)
    create_key = await client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"name": "test-key"},
    )
    assert create_key.status_code == 201, create_key.text
    api_key = create_key.json()["data"]["key"]

    response = await client.post(
        "/api/v1/events",
        headers={"X-API-Key": api_key},
        json={"event_name": "page_view", "properties": {"page": "/test"}},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["data"]["accepted"] == 1

    queued = await fake_redis.rpop(IngestionService.QUEUE_KEY)
    assert queued is not None
    payload = json.loads(queued)
    assert payload["event_name"] == "page_view"
    assert payload["organization_id"] == registered_user["organization_id"]


@pytest.mark.skipif(not INTEGRATION_ENABLED, reason="Set TEST_DATABASE_URL to run integration tests")
async def test_ingest_without_api_key_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/events",
        json={"event_name": "page_view"},
    )
    assert response.status_code == 401
