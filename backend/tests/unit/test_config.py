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
