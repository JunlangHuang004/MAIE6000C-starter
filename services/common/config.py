from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, Field, field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict
from pythonjsonlogger import jsonlogger


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/maie6000c"
    ai_service_url: str = "http://ai:8100"
    worker_poll_seconds: float = 2.0
    worker_request_timeout_seconds: float = 20.0
    nutrition_provider: Literal["demo", "qwen", "hkust", "ollama", "heuristic"] = "demo"
    llm_provider: Literal["demo", "qwen", "hkust", "ollama", "heuristic"] | None = None
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_api_key_header: str = "api-key"
    llm_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    dashscope_api_key: SecretStr = SecretStr("")
    qwen_base_url: str = ""
    qwen_model: str = "qwen-plus"
    qwen_timeout_seconds: float = Field(default=12.0, gt=0)
    auth_cookie_secure: bool = True
    auth_public_origin: str = "http://localhost:8000"
    auth_registration_enabled: bool = False
    auth_session_ttl_seconds: int = Field(default=8 * 60 * 60, ge=300, le=7 * 24 * 60 * 60)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("llm_provider", mode="before")
    @classmethod
    def empty_llm_provider_is_unset(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def effective_nutrition_provider(self) -> str:
        """The course selector overrides the legacy selector only when configured."""
        provider = self.llm_provider or self.nutrition_provider
        return "demo" if provider == "heuristic" else provider


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


class ServiceJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        if "service" not in log_record:
            parts = record.name.split(".")
            log_record["service"] = parts[1] if len(parts) > 1 and parts[0] == "services" else "app"


def configure_logging() -> None:
    if getattr(configure_logging, "_configured", False):
        return

    settings = get_settings()
    handler = logging.StreamHandler()
    handler.setFormatter(
        ServiceJsonFormatter("%(asctime)s %(levelname)s %(service)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    configure_logging._configured = True  # type: ignore[attr-defined]
