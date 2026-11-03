import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "shared" / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    trace: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text())
    return trace


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
