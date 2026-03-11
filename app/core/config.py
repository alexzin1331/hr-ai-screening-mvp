from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "HR AI Screening System"
    app_env: str = "development"
    api_prefix: str = "/api"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/hr_ai_screening"
    uploads_dir: Path = BASE_DIR / "uploads"

    llm_provider: str = "mock"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str | None = None
    llm_model: str = "llama-3.3-70b-versatile"
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 2
    llm_concurrency_limit: int = 4

    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_BOT_USERNAME", "BOT_USERNAME"),
    )
    telegram_api_base: str = "https://api.telegram.org"
    telegram_timeout_seconds: float = 15.0
    telegram_webhook_secret: str | None = None
    telegram_polling_enabled: bool = False
    telegram_polling_timeout_seconds: int = 25
    telegram_polling_retry_delay_seconds: float = 3.0

    invite_token_ttl_hours: int = 168

    email_provider: str = "resend"
    resend_api_key: str | None = Field(default=None, validation_alias="RESEND_API_KEY")
    resend_email_from: str = Field(
        default="HR AI Screening <onboarding@resend.dev>",
        validation_alias=AliasChoices("RESEND_EMAIL_FROM", "EMAIL_FROM_ADDRESS"),
    )
    email_from_address: str = "hr-screening@example.com"
    email_from_name: str = "HR AI Screening"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True

    processing_concurrency_limit: int = 4
    max_upload_size_mb: int = 50
    zip_max_members: int = 200
    zip_max_total_size_mb: int = 200

    default_hr_email: str = "hr@example.com"
    default_hr_password: str = "change-me"
    default_hr_company: str = "Demo Company"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    return settings
