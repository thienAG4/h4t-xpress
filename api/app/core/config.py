from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Accept plain `postgresql://` URLs (Neon, Render) and adapt them for asyncpg.

    asyncpg does not understand libpq options such as `sslmode` or `channel_binding`,
    so `sslmode=require` becomes `ssl=require` and unsupported options are dropped.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    query = []
    for key, value in parse_qsl(parts.query):
        if key == "sslmode":
            query.append(("ssl", value))
        elif key in ("channel_binding",):
            continue
        else:
            query.append((key, value))
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://h4t:h4t_dev_password@localhost:5432/h4t"

    demo_mode: bool = True
    demo_password: str = "Demo@12345"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # Auth (SPEC §5.2)
    # Development default only; production must set a random value of 32+ characters.
    jwt_secret: str = "dev-only-jwt-secret-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    refresh_cookie_name: str = "h4t_refresh"
    cookie_secure: bool = False
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5
    login_attempts_per_minute: int = 10

    file_storage: str = "local"
    upload_dir: str = "uploads"

    shopnow_api_key: str = "shopnow-demo-key"
    shopnow_webhook_secret: str = "shopnow-demo-webhook-secret"
    shopnow_webhook_url: str = "http://localhost:8000/api/v1/sim/shopnow/webhooks"

    seed_history_days: int = 90
    seed_random_seed: int = 11

    # Background worker (SPEC §5.6). Tests turn it off and call the job functions directly.
    worker_enabled: bool = True
    worker_poll_seconds: float = 1.0
    worker_sweep_seconds: float = 5.0

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @model_validator(mode="after")
    def _require_strong_secret_in_production(self) -> "Settings":
        if self.app_env == "production" and len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must have at least 32 characters in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
