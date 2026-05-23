from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Analytics Platform"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://analytics:analytics@localhost:5432/analytics"
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jwt_secret_key: str = "change-me-to-a-long-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000"

    ingest_rate_limit_per_minute: int = 10000

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_from: str | None = None

    frontend_url: str = "http://localhost:3000"

    cookie_secure: bool = False
    cookie_samesite: str = "lax"  # lax | none | strict (use none + secure for cross-origin SPA)
    cookie_domain: str | None = None

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def normalize_cookie_samesite(cls, v: str | None) -> str:
        if v is None or not str(v).strip():
            return "lax"
        normalized = str(v).strip().lower()
        if normalized not in ("lax", "none", "strict"):
            raise ValueError("cookie_samesite must be lax, none, or strict")
        return normalized

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | List[str] | None) -> str:
        if v is None:
            return ""
        if isinstance(v, list):
            return ",".join(str(item).strip() for item in v if str(item).strip())
        text = str(v).strip()
        return text

    @property
    def cors_origins_list(self) -> List[str]:
        """Parsed CORS origins; never returns [''] for empty/unset env (unlike raw split)."""
        if not self.cors_origins.strip():
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
