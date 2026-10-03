"""Plain domain vocabulary shared by all layers. Must not import anything from the app."""

from flow_tracer_api.domain.trace_status import TraceStatus

__all__ = ["TraceStatus"]
