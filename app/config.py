from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./invoice_recon.db"

    # AI settings (optional)
    ai_provider: str = "disabled"  # disabled|openai|mock
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"  # any chat model
    ai_timeout_seconds: float = 4.0


settings = Settings()
