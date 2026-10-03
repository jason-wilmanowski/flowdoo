"""Application settings, read from environment variables (and a local .env file)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator
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
    # dry_run=false writes to the user's Odoo DB. Dev setups only, off by default.
    allow_non_dry_run: bool = False

    # The frontend's URL (FRONTEND_URL); the only origin allowed to call the API (CORS).
    frontend_url: str

    # Connection to the user's existing Odoo 19 (never stored in the database).
    odoo_url: HttpUrl | None = None
    odoo_db: str | None = None
    # Optional: if set, the connection check verifies the API key belongs to this login.
    odoo_login: str | None = None
    odoo_api_key: SecretStr | None = None
    odoo_timeout_seconds: float = Field(default=10.0, gt=0)

    @field_validator("odoo_url", "odoo_db", "odoo_login", "odoo_api_key", mode="before")
    @classmethod
    def _empty_means_unset(cls, value: object) -> object:
        # Compose passes unset variables as empty strings.
        return None if value == "" else value

    @property
    def odoo_configured(self) -> bool:
        return self.odoo_url is not None and bool(self.odoo_db) and self.odoo_api_key is not None

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
