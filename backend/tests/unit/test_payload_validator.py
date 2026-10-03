from typing import Any

import pytest

from flow_tracer_api.services.ports import OpaquePayloadValidator, PayloadValidationError


def test_accepts_json_object_and_returns_copy() -> None:
    payload = {"steps": [{"id": "s1", "changes": []}], "dry_run": True}

    validated = OpaquePayloadValidator().validate(payload)

    assert validated.payload == payload
    assert validated.payload is not payload
    assert validated.schema_version is None


@pytest.mark.parametrize(
    "payload",
    [
        {"value": float("nan")},
        {"value": object()},
        {"value": {1, 2}},
    ],
)
def test_rejects_values_jsonb_cannot_store(payload: dict[str, Any]) -> None:
    with pytest.raises(PayloadValidationError, match="not valid JSON"):
        OpaquePayloadValidator().validate(payload)


def test_rejects_non_objects() -> None:
    with pytest.raises(PayloadValidationError, match="JSON object"):
        OpaquePayloadValidator().validate(["not", "an", "object"])  # type: ignore[arg-type]
