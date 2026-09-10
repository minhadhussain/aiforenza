from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_env_file(source: Path = Path(__file__)) -> Path:
    """Find the monorepo env independently of cwd, also supporting /app containers."""
    source = source.resolve()
    for parent in source.parents:
        if parent / "apps/api/app/core/config.py" == source:
            return parent / ".env"
    return source.parents[2] / ".env"


ROOT_ENV_FILE = resolve_env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    api_env: str = Field(default="development", alias="API_ENV")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_cors_origins: str = Field(
        default="http://localhost:3000", alias="API_CORS_ORIGINS"
    )
    api_key_pepper: str = Field(default="", alias="API_KEY_PEPPER")
    api_max_request_bytes: int = Field(default=200_000, alias="API_MAX_REQUEST_BYTES")
    api_max_messages: int = Field(default=100, alias="API_MAX_MESSAGES")
    api_requests_per_minute_per_key: int = Field(
        default=60, alias="API_REQUESTS_PER_MINUTE_PER_KEY"
    )
    api_requests_per_minute_per_user: int = Field(
        default=60, alias="API_REQUESTS_PER_MINUTE_PER_USER"
    )
    api_max_concurrent_requests: int = Field(
        default=10, alias="API_MAX_CONCURRENT_REQUESTS"
    )
    database_url: str = Field(default="", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(
        default="", alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_domestic_currency: str = Field(
        default="inr", alias="STRIPE_DOMESTIC_CURRENCY"
    )
    stripe_fx_rate_api_url: str = Field(
        default="https://open.er-api.com/v6/latest/USD", alias="STRIPE_FX_RATE_API_URL"
    )
    next_public_app_url: str = Field(
        default="http://localhost:3000", alias="NEXT_PUBLIC_APP_URL"
    )
    azure_api_key: str = Field(default="", alias="AZURE_API_KEY")
    azure_endpoint: str = Field(default="", alias="AZURE_ENDPOINT")
    litellm_url: str = Field(default="http://litellm:4000", alias="LITELLM_URL")
    litellm_master_key: str = Field(default="", alias="LITELLM_MASTER_KEY")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    posthog_key: str = Field(default="", alias="POSTHOG_KEY")
    posthog_host: str = Field(default="", alias="POSTHOG_HOST")

    @property
    def cors_origins(self) -> list[str]:
        configured = [
            origin.strip()
            for origin in self.api_cors_origins.split(",")
            if origin.strip()
        ]
        expanded: list[str] = []

        for origin in configured:
            if origin not in expanded:
                expanded.append(origin)

            parsed = urlsplit(origin)
            host = parsed.hostname
            if host not in {"localhost", "127.0.0.1"}:
                continue

            sibling_host = "127.0.0.1" if host == "localhost" else "localhost"
            sibling = f"{parsed.scheme}://{sibling_host}"
            if parsed.port is not None:
                sibling += f":{parsed.port}"
            if sibling not in expanded:
                expanded.append(sibling)

        return expanded


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
