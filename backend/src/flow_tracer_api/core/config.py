"""Application settings, read from environment variables (and a local .env file)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_ASYNC_DRIVER_PREFIX = "postgresql+asyncpg://"


class Settings(BaseSettings):
    """Runtime configuration.

    Secrets are ``SecretStr`` so they never show up in ``repr()`` or logs.
    The .env file is looked up relative to the working directory: ``backend/`` (local runs)
    falls back to the repository root. In containers, plain environment variables are used.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: SecretStr
    log_level: LogLevel = "INFO"

    @field_validator("database_url")
    @classmethod
    def _require_asyncpg(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(_ASYNC_DRIVER_PREFIX):
            raise ValueError(f"DATABASE_URL must start with {_ASYNC_DRIVER_PREFIX!r}")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings (cached)."""
    return Settings()  # values come from the environment
