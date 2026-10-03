"""Translate service errors into HTTP responses. Endpoints never catch them themselves."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from flow_tracer_api.services import (
    NonDryRunNotAllowedError,
    OdooGatewayUnavailableError,
    ServiceError,
    TraceNotFoundError,
)

_STATUS_BY_ERROR: dict[type[ServiceError], int] = {
    TraceNotFoundError: status.HTTP_404_NOT_FOUND,
    NonDryRunNotAllowedError: status.HTTP_403_FORBIDDEN,
    OdooGatewayUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


class ErrorResponse(BaseModel):
    detail: str


def _status_for(exc: ServiceError) -> int:
    for error_type, code in _STATUS_BY_ERROR.items():
        if isinstance(exc, error_type):
            return code
    return status.HTTP_400_BAD_REQUEST


async def _handle_service_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ServiceError)
    body = ErrorResponse(detail=str(exc))
    return JSONResponse(status_code=_status_for(exc), content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, _handle_service_error)


def error_responses(*codes: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI documentation of the error bodies an endpoint can return."""
    return {code: {"model": ErrorResponse} for code in codes}
