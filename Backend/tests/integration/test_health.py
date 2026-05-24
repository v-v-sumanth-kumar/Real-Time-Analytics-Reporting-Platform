import pytest
from httpx import AsyncClient

from tests.conftest import INTEGRATION_ENABLED

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not INTEGRATION_ENABLED, reason="Set TEST_DATABASE_URL to run integration tests")
async def test_health_reports_ok(
    client: AsyncClient,
    integration_db_ready: bool,
) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("healthy", "degraded")
    assert body["checks"]["api"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"
