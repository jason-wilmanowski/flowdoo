"""Trace endpoints. Thin: call the injected TraceService, translate its errors, return DTOs.

The service arrives via ``TraceServiceDep``: FastAPI opens one ``AsyncSession`` per
request (``core.dependencies.get_session``) and passes it to ``TraceService``.
Every ``ServiceError`` carries ``message`` and ``status_code``; each endpoint catches it
and raises the matching ``HTTPException``.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from flow_tracer_api.api.dependencies import TraceServiceDep
from flow_tracer_api.api.schemas import error_responses
from flow_tracer_api.schemas import StartTraceCommand, TraceDetail, TraceListQuery, TracePage
from flow_tracer_api.services import ServiceError

router = APIRouter(prefix="/traces", tags=["traces"])


def _http_error(exc: ServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Record a workflow run in the connected Odoo",
    description=(
        "Runs the entrypoint in the user's Odoo and stores the recorded trace. "
        "The response is the stored trace: `status` is `succeeded` or `failed` "
        "(with `error`), a failed recording is still a created trace. "
        "`dry_run=false` is rejected unless ALLOW_NON_DRY_RUN is enabled."
    ),
    responses=error_responses(
        status.HTTP_403_FORBIDDEN, status.HTTP_409_CONFLICT, status.HTTP_503_SERVICE_UNAVAILABLE
    ),
)
async def start_trace(command: StartTraceCommand, service: TraceServiceDep) -> TraceDetail:
    try:
        return await service.start_trace(command)
    except ServiceError as exc:
        raise _http_error(exc) from exc


@router.get(
    "",
    summary="List traces, newest first",
    description="Without payloads. Filter by status and entrypoint; page with limit/offset.",
)
async def list_traces(
    query: Annotated[TraceListQuery, Query()], service: TraceServiceDep
) -> TracePage:
    try:
        return await service.list_traces(query)
    except ServiceError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/{trace_id}",
    summary="Get one trace including its payload",
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def get_trace(trace_id: uuid.UUID, service: TraceServiceDep) -> TraceDetail:
    try:
        return await service.get_trace(trace_id)
    except ServiceError as exc:
        raise _http_error(exc) from exc


@router.delete(
    "/{trace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a trace",
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def delete_trace(trace_id: uuid.UUID, service: TraceServiceDep) -> None:
    try:
        await service.delete_trace(trace_id)
    except ServiceError as exc:
        raise _http_error(exc) from exc
