from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://finquery:finquery@localhost:5432/finquery"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_access_key: str = "finquery"
    s3_secret_key: str = "finquery-secret"
    s3_bucket: str = "invoices"
    s3_region: str = "us-east-1"

    groq_api_key: str | None = None
    extraction_model: str = "llama-3.3-70b-versatile"
    # Characters of document text sent to the extraction model. Longer documents
    # are truncated and flagged on the invoice so a reviewer knows.
    extraction_max_chars: int = 30_000

    max_upload_mb: int = 20
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
