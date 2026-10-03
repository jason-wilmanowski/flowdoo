"""SQLAlchemy ORM models. Pure table mapping, no logic."""

from flow_tracer_api.models.base import Base
from flow_tracer_api.models.trace import Trace

__all__ = ["Base", "Trace"]
