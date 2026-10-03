import pytest
from pydantic import SecretStr, ValidationError

from flow_tracer_api.core.config import Settings


def test_database_url_must_use_asyncpg() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+asyncpg://"):
        Settings(database_url=SecretStr("postgresql://u:p@localhost/x"), _env_file=None)


def test_database_url_is_not_leaked_in_repr() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+asyncpg://u:topsecret@localhost/x"), _env_file=None
    )

    assert "topsecret" not in repr(settings)


def test_odoo_settings_default_to_unconfigured() -> None:
    settings = Settings(database_url=SecretStr("postgresql+asyncpg://u:p@h/x"), _env_file=None)

    assert settings.odoo_configured is False
    assert settings.odoo_url is None


def test_empty_odoo_variables_count_as_unset() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+asyncpg://u:p@h/x"),
        odoo_url="",
        odoo_db="",
        odoo_api_key="",
        _env_file=None,
    )

    assert settings.odoo_configured is False


def test_odoo_configured_needs_url_db_and_key_and_hides_key() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+asyncpg://u:p@h/x"),
        odoo_url="http://localhost:8069",
        odoo_db="dev",
        odoo_api_key=SecretStr("abc123secret"),
        _env_file=None,
    )

    assert settings.odoo_configured is True
    assert "abc123secret" not in repr(settings)
