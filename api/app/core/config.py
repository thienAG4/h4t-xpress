from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
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
    jwt_secret: str = "change-me"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    file_storage: str = "local"
    upload_dir: str = "uploads"

    shopnow_api_key: str = "shopnow-demo-key"
    shopnow_webhook_secret: str = "shopnow-demo-webhook-secret"
    shopnow_webhook_url: str = "http://localhost:8000/api/v1/sim/shopnow/webhooks"

    seed_history_days: int = 90
    seed_random_seed: int = 11

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
