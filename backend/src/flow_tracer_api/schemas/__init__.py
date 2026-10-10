"""Pydantic v2 models for all data passed between layers. Never ORM objects."""

from flow_tracer_api.schemas.odoo import (
    EntrypointParameter,
    EntrypointSignature,
    GatewayResult,
    OdooConnectionStatus,
    OdooVersionInfo,
    TraceRequest,
    ValidatedPayload,
)
from flow_tracer_api.schemas.registry import (
    ModelDetail,
    ModelField,
    ModelList,
    ModelRelation,
    ModelSummary,
)
from flow_tracer_api.schemas.trace import (
    StartTraceCommand,
    TraceDetail,
    TraceListQuery,
    TracePage,
    TraceSummary,
)
from flow_tracer_api.schemas.trace_persistence import TraceCreate, TraceFilter, TraceUpdate

__all__ = [
    "EntrypointParameter",
    "EntrypointSignature",
    "GatewayResult",
    "ModelDetail",
    "ModelField",
    "ModelList",
    "ModelRelation",
    "ModelSummary",
    "OdooConnectionStatus",
    "OdooVersionInfo",
    "StartTraceCommand",
    "TraceCreate",
    "TraceDetail",
    "TraceFilter",
    "TraceListQuery",
    "TracePage",
    "TraceRequest",
    "TraceSummary",
    "TraceUpdate",
    "ValidatedPayload",
]
