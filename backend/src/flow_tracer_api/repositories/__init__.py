"""Repository layer: the only place that runs queries.

Repositories work on the session they are constructed with and never commit;
committing is the service layer's decision. Their inputs are Pydantic models from
``schemas``.
"""

from flow_tracer_api.repositories.protocols import TraceRepository

__all__ = ["TraceRepository"]
