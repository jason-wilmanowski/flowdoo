from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    odoo_url: str
    odoo_db: str
    odoo_api_key: str
    flowdoo_timeout: float = 30.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
