"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment_main: str = "gpt-4o-2"
    azure_openai_deployment_fast: str = "gpt-4.1-nano-2"
    app_name: str = "SJ Project Planner Agent"
    log_level: str = "INFO"
    webhook_api_key: str = "change-me-in-production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
