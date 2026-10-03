"""Trace runs through the flow_tracer addon (``POST /flow_tracer/v1/trace``)."""

from typing import Any

from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from flow_tracer_api.integrations.odoo.errors import OdooCallError, OdooDatabaseNotFoundError
from flow_tracer_api.schemas import GatewayResult, TraceRequest

TRACE_ROUTE = "/flow_tracer/v1/trace"


class FlowTracerGateway:
    """Implements the service port ``OdooGateway`` with the addon's trace endpoint.

    Errors are ``OdooClientError`` subclasses; their messages contain no credentials.
    """

    def __init__(self, client: OdooJson2Client, *, timeout_seconds: float) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    async def run_trace(self, request: TraceRequest) -> GatewayResult:
        body: dict[str, Any] = {
            "trace_id": str(request.trace_id),
            "model": request.model,
            "method": request.method,
            "record_ids": list(request.record_ids),
            "context": dict(request.context),
            "dry_run": request.dry_run,
        }
        try:
            payload = await self._client.post(
                TRACE_ROUTE,
                body,
                timeout_seconds=self._timeout_seconds,
                target="flow_tracer trace",
            )
        except OdooDatabaseNotFoundError as exc:
            # A plain 404 page: unknown database, or the addon's route does not exist.
            raise OdooCallError(
                f"{exc.message}; or the flow_tracer addon is not installed/up to date"
            ) from exc
        if not isinstance(payload, dict):
            raise OdooCallError(
                f"flow_tracer answered with {type(payload).__name__}, expected a trace object"
            )
        version = payload.get("odoo_version")
        return GatewayResult(
            payload=payload, odoo_version=version if isinstance(version, str) else None
        )
