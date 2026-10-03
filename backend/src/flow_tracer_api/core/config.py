"""Application settings, read from environment variables (and a local .env file)."""

import re
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_ASYNC_DRIVER_PREFIX = "postgresql+asyncpg://"

# Vite dev server of the frontend service (CLAUDE.md section 3).
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
_ORIGIN_PATTERN = re.compile(r"https?://[A-Za-z0-9.-]+(:\d{1,5})?")


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

    # Browser origins allowed to call the API (the frontend). Comma-separated in the
    # environment, e.g. CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ORIGINS)
    )

    # Connection to the user's existing Odoo 19 (never stored in the database).
    odoo_url: HttpUrl | None = None
    odoo_db: str | None = None
    # Optional: if set, the connection check verifies the API key belongs to this login.
    odoo_login: str | None = None
    odoo_api_key: SecretStr | None = None
    odoo_timeout_seconds: float = Field(default=10.0, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def _require_exact_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            if not _ORIGIN_PATTERN.fullmatch(origin):
                raise ValueError(
                    f"Invalid CORS origin {origin!r}: use scheme://host[:port] without path, "
                    "trailing slash or wildcard"
                )
        return origins

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
