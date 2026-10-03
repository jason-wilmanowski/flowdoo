"""Describe an entrypoint before tracing it (flow_tracer addon, /flow_tracer/v1/signature)."""

from http import HTTPStatus

from pydantic import ValidationError

from flow_tracer_api.integrations.odoo import OdooCallError, OdooClientError
from flow_tracer_api.schemas import EntrypointSignature
from flow_tracer_api.services.errors import (
    EntrypointLookupError,
    OdooGatewayUnavailableError,
    OdooRequestError,
)
from flow_tracer_api.services.ports import OdooClient

SIGNATURE_ROUTE = "/flow_tracer/v1/signature"
# Odoo answers that are about the request itself and are passed on as they are.
_PASSED_ON = {HTTPStatus.BAD_REQUEST, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND}


class EntrypointService:
    def __init__(self, client: OdooClient | None) -> None:
        self._client = client

    async def describe(self, model: str, method: str) -> EntrypointSignature:
        if self._client is None:
            raise OdooGatewayUnavailableError(
                message="No connection to Odoo is configured",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        try:
            answer = await self._client.post(
                SIGNATURE_ROUTE,
                {"model": model, "method": method},
                target=f"{model}.{method} signature",
            )
        except OdooCallError as exc:
            if exc.status_code in _PASSED_ON:
                raise EntrypointLookupError(
                    message=exc.message, status_code=HTTPStatus(exc.status_code)
                ) from exc
            raise OdooRequestError(message=exc.message, status_code=HTTPStatus.BAD_GATEWAY) from exc
        except OdooClientError as exc:
            raise OdooRequestError(message=exc.message, status_code=HTTPStatus.BAD_GATEWAY) from exc
        try:
            return EntrypointSignature.model_validate(answer)
        except ValidationError as exc:
            raise OdooRequestError(
                message=f"Unexpected signature answer from flow_tracer: {exc.error_count()} errors",
                status_code=HTTPStatus.BAD_GATEWAY,
            ) from exc
