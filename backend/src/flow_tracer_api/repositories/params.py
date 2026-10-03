"""Typed inputs of repository operations (plain dataclasses, no ORM, no Pydantic)."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Final, Literal

from flow_tracer_api.domain import TraceStatus


class Unset(Enum):
    """Marks a field of ``TraceUpdate`` as 'leave unchanged' (``None`` means 'set NULL')."""

    UNSET = "UNSET"


UNSET: Final[Literal[Unset.UNSET]] = Unset.UNSET


@dataclass(frozen=True, slots=True, kw_only=True)
class TraceCreate:
    entrypoint_model: str
    entrypoint_method: str
    started_at: datetime
    dry_run: bool = True
    status: TraceStatus = TraceStatus.PENDING
    id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class TraceUpdate:
    status: TraceStatus | Unset = UNSET
    schema_version: str | Unset | None = UNSET
    odoo_version: str | Unset | None = UNSET
    finished_at: datetime | Unset | None = UNSET
    error: str | Unset | None = UNSET
    payload: dict[str, Any] | Unset | None = UNSET

    def changed_fields(self) -> dict[str, Any]:
        return {
            name: value for name in self.__slots__ if (value := getattr(self, name)) is not UNSET
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class TraceFilter:
    status: TraceStatus | None = None
    entrypoint_model: str | None = None
    entrypoint_method: str | None = None
