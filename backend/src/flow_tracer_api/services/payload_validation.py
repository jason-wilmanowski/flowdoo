"""Validation of recorder output against the trace schema (shared/schemas)."""

import json
from collections.abc import Mapping, Sequence
from typing import Any, get_args

from pydantic import ValidationError

from flow_tracer_api.generated.trace_schema import Step, TracePayload
from flow_tracer_api.schemas import ValidatedPayload
from flow_tracer_api.services.ports import PayloadValidationError

_MAX_REPORTED_ERRORS = 5

# The version the generated model accepts, e.g. "0.2.0" (single source: the schema).
SCHEMA_VERSION: str = get_args(TracePayload.model_fields["schema_version"].annotation)[0]


class SchemaPayloadValidator:
    """Checks a payload against the generated schema model plus the step-tree rules
    JSON Schema cannot express (unique ids and seq, parent_id must exist).

    The stored payload is the original JSON, not a re-serialised model, so values such as
    integers in field changes are kept exactly as the recorder sent them.
    """

    def validate(self, payload: Mapping[str, Any]) -> ValidatedPayload:
        if not isinstance(payload, Mapping):
            raise PayloadValidationError(
                f"Trace payload must be a JSON object, got {type(payload).__name__}"
            )
        try:
            normalised = json.loads(json.dumps(dict(payload), allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise PayloadValidationError(f"Trace payload is not valid JSON: {exc}") from exc
        try:
            trace = TracePayload.model_validate(normalised)
        except ValidationError as exc:
            raise PayloadValidationError(_describe(exc)) from exc
        _check_step_tree(trace.steps)
        return ValidatedPayload(payload=normalised, schema_version=trace.schema_version)


def _describe(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False, include_input=False)
    parts = [f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in errors]
    shown = "; ".join(parts[:_MAX_REPORTED_ERRORS])
    more = len(parts) - _MAX_REPORTED_ERRORS
    suffix = f" (and {more} more)" if more > 0 else ""
    return f"Trace payload does not match schema {SCHEMA_VERSION}: {shown}{suffix}"


def _check_step_tree(steps: Sequence[Step]) -> None:
    ids: set[str] = set()
    seqs: set[int] = set()
    for step in steps:
        if step.id in ids:
            raise PayloadValidationError(f"Duplicate step id {step.id!r}")
        if step.seq in seqs:
            raise PayloadValidationError(f"Duplicate step seq {step.seq}")
        ids.add(step.id)
        seqs.add(step.seq)
    for step in steps:
        if step.parent_id is not None and (step.parent_id not in ids or step.parent_id == step.id):
            raise PayloadValidationError(
                f"Step {step.id!r} has unknown parent_id {step.parent_id!r}"
            )
