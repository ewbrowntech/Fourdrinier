"""Application configuration loaded from environment variables and optional .env."""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["critical", "error", "warning", "info", "debug", "trace"]
AppEnv = Literal["debug", "dev", "stage", "prod", "test"]

# src/backend/fourdrinier/core/settings.py -> repo root (fourdrinier/)
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: AppEnv = "dev"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)

    log_level: LogLevel = "info"

    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"
    openapi_url: str | None = "/openapi.json"

    web_concurrency: int | None = Field(default=None, ge=1)

    gunicorn_timeout: int = Field(default=120, ge=1)
    gunicorn_graceful_timeout: int = Field(default=30, ge=1)
    gunicorn_max_requests: int = Field(default=1000, ge=0)
    gunicorn_max_requests_jitter: int = Field(default=100, ge=0)
    gunicorn_preload: bool = True

    @field_validator("env", "log_level", mode="before")
    @classmethod
    def _normalize_lowercase(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower()
        return value

    @field_validator("docs_url", "redoc_url", "openapi_url", mode="before")
    @classmethod
    def _empty_str_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def is_debug_server(self) -> bool:
        """True when running uvicorn with auto-reload (local development only)."""
        return self.env == "debug"

    def worker_count(self) -> int:
        if self.web_concurrency is not None:
            return self.web_concurrency
        return max(1, (multiprocessing.cpu_count() * 2) + 1)


SETTINGS = Settings()


__all__ = ["AppEnv", "LogLevel", "SETTINGS", "Settings"]
