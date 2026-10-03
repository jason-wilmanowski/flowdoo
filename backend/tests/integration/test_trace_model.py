import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.models import Trace

pytestmark = pytest.mark.integration


def _trace(**overrides: object) -> Trace:
    values: dict[str, object] = {
        "status": TraceStatus.RUNNING,
        "entrypoint_model": "sale.order",
        "entrypoint_method": "action_confirm",
        "started_at": datetime(2026, 10, 3, 12, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return Trace(**values)


async def test_insert_applies_defaults(db_session: AsyncSession) -> None:
    trace = _trace()
    db_session.add(trace)
    await db_session.flush()
    await db_session.refresh(trace)

    assert isinstance(trace.id, uuid.UUID)
    assert trace.dry_run is True
    assert trace.created_at.tzinfo is not None
    assert trace.payload is None
    assert trace.finished_at is None


async def test_payload_roundtrips_as_jsonb(db_session: AsyncSession) -> None:
    payload = {"schema_version": "0.1.0", "steps": [{"id": "s1", "changes": []}]}
    trace = _trace(status=TraceStatus.SUCCEEDED, payload=payload)
    db_session.add(trace)
    await db_session.flush()
    db_session.expunge_all()

    loaded = await db_session.scalar(select(Trace).where(Trace.id == trace.id))
    assert loaded is not None
    assert loaded.payload == payload
    assert loaded.status is TraceStatus.SUCCEEDED
    jsonb_type = await db_session.scalar(
        text("SELECT jsonb_typeof(payload) FROM traces WHERE id = :id"), {"id": trace.id}
    )
    assert jsonb_type == "object"


async def test_status_check_constraint_rejects_unknown_value(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="ck_traces_trace_status"):
        await db_session.execute(
            text(
                "INSERT INTO traces (id, status, entrypoint_model, entrypoint_method, started_at)"
                " VALUES (:id, 'bogus', 'sale.order', 'action_confirm', now())"
            ),
            {"id": uuid.uuid4()},
        )


async def test_entrypoint_is_required(db_session: AsyncSession) -> None:
    db_session.add(_trace(entrypoint_model=None))
    with pytest.raises(IntegrityError):
        await db_session.flush()
