import pytest
from httpx import AsyncClient

from tests.conftest import INTEGRATION_ENABLED, auth_headers

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not INTEGRATION_ENABLED, reason="Set TEST_DATABASE_URL to run integration tests")
async def test_signup_login_and_me(
    client: AsyncClient,
    registered_user: dict,
) -> None:
    headers = auth_headers(registered_user)
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["success"] is True
    assert body["data"]["user"]["email"] == registered_user["email"]
    assert body["data"]["organization"]["id"] == registered_user["organization_id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert login.status_code == 200
    assert login.json()["data"]["access_token"]


@pytest.mark.skipif(not INTEGRATION_ENABLED, reason="Set TEST_DATABASE_URL to run integration tests")
async def test_login_invalid_password_returns_401(
    client: AsyncClient,
    registered_user: dict,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False
