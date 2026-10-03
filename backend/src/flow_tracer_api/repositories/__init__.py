"""Repository layer: the only place that talks to the database.

Repositories never commit; transaction boundaries belong to the service layer, which
drives them through a ``UnitOfWork``. Their inputs are Pydantic models from ``schemas``.
"""

from flow_tracer_api.repositories.protocols import TraceRepository, UnitOfWork

__all__ = ["TraceRepository", "UnitOfWork"]
