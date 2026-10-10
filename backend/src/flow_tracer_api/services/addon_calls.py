"""Ask a read-only route of the flow_tracer addon and map its errors to service errors."""

from http import HTTPStatus
from typing import Any

from pydantic import BaseModel, ValidationError

from flow_tracer_api.integrations.odoo import OdooCallError, OdooClientError
from flow_tracer_api.services.errors import (
    OdooGatewayUnavailableError,
    OdooRequestError,
    ServiceError,
)
from flow_tracer_api.services.ports import OdooClient

# Odoo answers that are about the request itself and are passed on as they are.
PASSED_ON = {HTTPStatus.BAD_REQUEST, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND}


async def ask_addon[Answer: BaseModel](
    client: OdooClient | None,
    route: str,
    payload: dict[str, Any],
    *,
    target: str,
    answer_type: type[Answer],
    refused: type[ServiceError],
) -> Answer:
    """POST to ``route`` and validate the answer as ``answer_type``.

    Raises ``refused`` for 400/403/404 from Odoo (with Odoo's message), OdooRequestError
    (502) for anything else that goes wrong, OdooGatewayUnavailableError (503) without a
    configured connection.
    """
    if client is None:
        raise OdooGatewayUnavailableError(
            message="No connection to Odoo is configured",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )
    try:
        answer = await client.post(route, payload, target=target)
    except OdooCallError as exc:
        if exc.status_code in PASSED_ON:
            raise refused(message=exc.message, status_code=HTTPStatus(exc.status_code)) from exc
        raise OdooRequestError(message=exc.message, status_code=HTTPStatus.BAD_GATEWAY) from exc
    except OdooClientError as exc:
        raise OdooRequestError(message=exc.message, status_code=HTTPStatus.BAD_GATEWAY) from exc
    try:
        return answer_type.model_validate(answer)
    except ValidationError as exc:
        raise OdooRequestError(
            message=f"Unexpected answer from flow_tracer ({target}): {exc.error_count()} errors",
            status_code=HTTPStatus.BAD_GATEWAY,
        ) from exc
