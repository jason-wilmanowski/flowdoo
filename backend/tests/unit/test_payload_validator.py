import copy
from typing import Any

import jsonschema
import pytest

from flow_tracer_api.services.payload_validation import SchemaPayloadValidator
from flow_tracer_api.services.ports import PayloadValidationError
from tests.fixtures import FIXTURE_NAMES, load_fixture, load_schema


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixtures_match_the_json_schema(name: str) -> None:
    validator = jsonschema.Draft202012Validator(
        load_schema(), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )

    validator.validate(load_fixture(name))


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixtures_pass_the_backend_validator_unchanged(name: str) -> None:
    payload = load_fixture(name)

    validated = SchemaPayloadValidator().validate(payload)

    assert validated.schema_version == "0.1.0"
    assert validated.payload == payload  # stored as sent, not re-serialised
    assert validated.payload is not payload


def test_integer_field_values_are_not_turned_into_floats() -> None:
    validated = SchemaPayloadValidator().validate(load_fixture("trace-medium"))

    change = validated.payload["steps"][6]["changes"][0]
    assert change["field"] == "delivery_count"
    assert type(change["new"]) is int


def _broken(mutate: Any) -> dict[str, Any]:
    payload = copy.deepcopy(load_fixture("trace-small"))
    mutate(payload)
    return payload


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        (_broken(lambda p: p.update(schema_version="1.0.0")), "schema_version"),
        (_broken(lambda p: p.pop("steps")), "steps: Field required"),
        (_broken(lambda p: p.update(unexpected=1)), "unexpected: Extra inputs"),
        (_broken(lambda p: p["steps"][0].update(kind="teleport")), "steps.0.kind"),
        (_broken(lambda p: p["steps"][0].update(args_summary="x" * 2001)), "steps.0.args_summary"),
        (_broken(lambda p: p.update(started_at="2026-10-03T12:00:00")), "started_at"),
        (_broken(lambda p: p["entrypoint"].update(record_ids=[0])), "entrypoint.record_ids.0"),
    ],
)
def test_schema_violations_are_reported(payload: dict[str, Any], fragment: str) -> None:
    with pytest.raises(PayloadValidationError, match=r"does not match schema 0\.1\.0") as exc_info:
        SchemaPayloadValidator().validate(payload)

    assert fragment in exc_info.value.args[0]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p["steps"][1].update(id="s1"), "Duplicate step id 's1'"),
        (lambda p: p["steps"][1].update(seq=1), "Duplicate step seq 1"),
        (lambda p: p["steps"][1].update(parent_id="s99"), "unknown parent_id 's99'"),
        (lambda p: p["steps"][1].update(parent_id="s2"), "unknown parent_id 's2'"),
    ],
)
def test_step_tree_rules(mutate: Any, message: str) -> None:
    with pytest.raises(PayloadValidationError, match=message):
        SchemaPayloadValidator().validate(_broken(mutate))


def test_rejects_values_that_are_not_json() -> None:
    with pytest.raises(PayloadValidationError, match="not valid JSON"):
        SchemaPayloadValidator().validate(_broken(lambda p: p.update(odoo_version=float("nan"))))


def test_rejects_non_objects() -> None:
    with pytest.raises(PayloadValidationError, match="JSON object"):
        SchemaPayloadValidator().validate(["not", "an", "object"])  # type: ignore[arg-type]
