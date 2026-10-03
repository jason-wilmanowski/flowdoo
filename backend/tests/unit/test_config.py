import pytest
from pydantic import SecretStr, ValidationError

from flow_tracer_api.core.config import Settings
from tests.settings import make_settings


def test_database_url_must_use_asyncpg() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+asyncpg://"):
        make_settings(database_url=SecretStr("postgresql://u:p@localhost/x"))


def test_database_url_is_not_leaked_in_repr() -> None:
    settings = make_settings(database_url=SecretStr("postgresql+asyncpg://u:topsecret@localhost/x"))

    assert "topsecret" not in repr(settings)


def test_odoo_settings_default_to_unconfigured() -> None:
    settings = make_settings()

    assert settings.odoo_configured is False
    assert settings.odoo_url is None


def test_empty_odoo_variables_count_as_unset() -> None:
    settings = make_settings(
        odoo_url="",
        odoo_db="",
        odoo_api_key="",
    )

    assert settings.odoo_configured is False


def test_odoo_configured_needs_url_db_and_key_and_hides_key() -> None:
    settings = make_settings(
        odoo_url="http://localhost:8069",
        odoo_db="dev",
        odoo_api_key=SecretStr("abc123secret"),
    )

    assert settings.odoo_configured is True
    assert "abc123secret" not in repr(settings)


def test_frontend_url_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/x")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")

    assert Settings(_env_file=None).frontend_url == "http://localhost:3000"


def test_frontend_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/x")
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    with pytest.raises(ValidationError, match="frontend_url"):
        Settings(_env_file=None)
