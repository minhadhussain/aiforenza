from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_env: str = Field(default="development", alias="API_ENV")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_cors_origins: str = Field(default="http://localhost:3000", alias="API_CORS_ORIGINS")
    api_key_pepper: str = Field(default="", alias="API_KEY_PEPPER")
    database_url: str = Field(default="", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    azure_api_key: str = Field(default="", alias="AZURE_API_KEY")
    azure_endpoint: str = Field(default="", alias="AZURE_ENDPOINT")
    litellm_master_key: str = Field(default="", alias="LITELLM_MASTER_KEY")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    posthog_key: str = Field(default="", alias="POSTHOG_KEY")
    posthog_host: str = Field(default="", alias="POSTHOG_HOST")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
