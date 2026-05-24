"""Shared pytest fixtures.

Unit tests run with no external services.
Integration tests require PostgreSQL — set TEST_DATABASE_URL, e.g.:

  TEST_DATABASE_URL=postgresql+asyncpg://analytics:analytics@localhost:5432/analytics_test
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Configure test env before any app imports that read settings / create engines.
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-characters")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()

if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

INTEGRATION_ENABLED = bool(TEST_DATABASE_URL)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: requires PostgreSQL (TEST_DATABASE_URL)",
    )


@pytest.fixture(scope="session")
def integration_db_ready() -> bool:
    if not INTEGRATION_ENABLED:
        return False
    from app.core.config import get_settings

    get_settings.cache_clear()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.exit(
            f"alembic upgrade failed:\n{result.stderr or result.stdout}",
            returncode=1,
        )
    return True


@pytest_asyncio.fixture
async def fake_redis():
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def client(fake_redis) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.core.deps import get_redis
    from app.main import app

    get_settings.cache_clear()

    async def _redis_override():
        return fake_redis

    app.dependency_overrides[get_redis] = _redis_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, unique_email: str) -> dict:
    """Sign up a user + org; returns tokens and ids for integration tests."""
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "full_name": "Test User",
            "organization_name": "Test Org",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    return {
        "email": unique_email,
        "password": "testpassword123",
        "access_token": data["access_token"],
        "user_id": data["user"]["id"],
        "organization_id": data["organization"]["id"],
        "role": data["role"],
    }


def auth_headers(user: dict) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {user['access_token']}",
        "X-Organization-ID": user["organization_id"],
    }
