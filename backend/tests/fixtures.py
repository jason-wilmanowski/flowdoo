"""Access to the shared trace schema and fixtures (shared/ at the repository root)."""

import json
from pathlib import Path
from typing import Any

SHARED = Path(__file__).resolve().parents[2] / "shared"
SCHEMA_PATH = SHARED / "schemas" / "trace.schema.json"
FIXTURE_NAMES = ("trace-small", "trace-medium", "trace-error")


def load_fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((SHARED / "fixtures" / f"{name}.json").read_text())
    return data


def load_schema() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SCHEMA_PATH.read_text())
    return data
