"""Application settings, read from environment variables (and backend/.env locally)."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-secret-not-for-production-use"
BACKEND_DIR = Path(__file__).resolve().parents[2]  # .env and the dev database live next to the code


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    environment: str = "development"
    secret_key: str = DEV_SECRET
    access_token_expire_minutes: int = 1440

    database_url: str = ""
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    supabase_url: str = ""
    supabase_service_key: str = ""
    public_bucket: str = "public-media"
    private_bucket: str = "room-photos"
    media_dir: str = str(BACKEND_DIR / "media")

    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5-5"

    image_provider: str = "auto"
    cf_account_id: str = ""
    cf_api_token: str = ""
    studio_daily_limit: int = 20

    rate_limit_enabled: bool = True
    max_upload_bytes: int = 5 * 1024 * 1024

    @model_validator(mode="after")
    def _check_production(self):
        if self.environment == "production" and self.secret_key == DEV_SECRET:
            raise ValueError("SECRET_KEY must be set to a strong random value in production")
        return self

    @property
    def sqlalchemy_url(self) -> str:
        """Normalise the URL so SQLAlchemy uses the psycopg 3 driver for Postgres."""
        url = self.database_url or f"sqlite:///{(BACKEND_DIR / 'roomora.db').as_posix()}"
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_supabase_storage(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
