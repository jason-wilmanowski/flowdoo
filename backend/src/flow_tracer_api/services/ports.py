"""Ports to the outside world the service layer depends on.

Only interfaces live here. The Odoo connection (JSON-RPC/HTTP, credentials from .env)
is implemented later; credentials never pass through the service layer or the database.
"""

import json
from collections.abc import Mapping
from typing import Any, Protocol

from flow_tracer_api.schemas import GatewayResult, TraceRequest, ValidatedPayload


class OdooGatewayError(Exception):
    """Odoo unreachable, wrong version, addon missing, or the traced call failed.

    Implementations must keep credentials out of the message; it is stored as trace error.
    """


class OdooGateway(Protocol):
    async def run_trace(self, request: TraceRequest) -> GatewayResult:
        """Run ``request`` in the user's Odoo via the flow_tracer addon and return its trace."""
        ...


class PayloadValidationError(Exception):
    """The recorder returned something that is not a valid trace."""


class TracePayloadValidator(Protocol):
    def validate(self, payload: Mapping[str, Any]) -> ValidatedPayload: ...


class OpaquePayloadValidator:
    """Placeholder until ``shared/schemas/trace.schema.json`` exists.

    Only guarantees what storage needs: a JSON object that serialises to JSONB.
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
        # TODO(trace-schema): validate against the model generated from
        # shared/schemas/trace.schema.json and take schema_version from it.
        return ValidatedPayload(payload=normalised, schema_version=None)
