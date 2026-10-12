"""Ports to the outside world the service layer depends on.

Only interfaces live here. Implementations live in ``integrations`` (e.g. the Odoo JSON-2
client); credentials stay inside them and never pass through services or the database.
"""

from collections.abc import Mapping
from typing import Any, Protocol

from flow_tracer_api.integrations.odoo.errors import OdooClientError
from flow_tracer_api.schemas import GatewayResult, OdooVersionInfo, TraceRequest, ValidatedPayload

# Raised by OdooGateway implementations: Odoo unreachable, key rejected, addon missing or
# refusing, unusable answer. The message is stored as trace error, so it never contains
# credentials (guaranteed by the Odoo client).
OdooGatewayError = OdooClientError


class OdooGateway(Protocol):
    async def run_trace(self, request: TraceRequest) -> GatewayResult:
        """Run ``request`` in the user's Odoo via the flow_tracer addon and return its trace."""
        ...


class OdooClient(Protocol):
    """Low-level access to the user's Odoo (implemented by ``OdooJson2Client``).

    Raises ``integrations.odoo.OdooClientError`` subclasses on failure.
    """

    async def version_info(self) -> OdooVersionInfo: ...

    async def call(
        self,
        model: str,
        method: str,
        *,
        ids: list[int] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any: ...

    async def post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        target: str | None = None,
    ) -> Any: ...


class PayloadValidationError(Exception):
    """The recorder returned something that is not a valid trace."""


class TracePayloadValidator(Protocol):
    def validate(self, payload: Mapping[str, Any]) -> ValidatedPayload: ...
