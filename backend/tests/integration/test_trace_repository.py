import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.repositories import TraceCreate, TraceFilter, TraceRepository, TraceUpdate
from flow_tracer_api.repositories.sqlalchemy import SqlAlchemyTraceRepository

pytestmark = pytest.mark.integration

STARTED = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


@pytest.fixture
def repo(db_session: AsyncSession) -> TraceRepository:
    return SqlAlchemyTraceRepository(db_session)


def _new(model: str = "sale.order", method: str = "action_confirm", **kw: Any) -> TraceCreate:
    return TraceCreate(
        entrypoint_model=model, entrypoint_method=method, **{"started_at": STARTED, **kw}
    )


async def test_create_returns_persisted_trace_with_db_defaults(repo: TraceRepository) -> None:
    trace = await repo.create(_new())

    assert isinstance(trace.id, uuid.UUID)
    assert trace.status is TraceStatus.PENDING
    assert trace.dry_run is True
    assert trace.created_at is not None


async def test_create_keeps_given_id(repo: TraceRepository) -> None:
    trace_id = uuid.uuid4()

    trace = await repo.create(_new(id=trace_id, dry_run=False, status=TraceStatus.RUNNING))

    assert trace.id == trace_id
    assert trace.dry_run is False
    assert trace.status is TraceStatus.RUNNING


async def test_get_returns_none_for_unknown_id(repo: TraceRepository) -> None:
    assert await repo.get(uuid.uuid4()) is None


async def test_get_finds_created_trace(repo: TraceRepository, db_session: AsyncSession) -> None:
    created = await repo.create(_new())
    db_session.expunge_all()

    loaded = await repo.get(created.id)

    assert loaded is not None
    assert loaded.entrypoint_model == "sale.order"
    assert loaded.entrypoint_method == "action_confirm"


async def test_update_changes_only_given_fields(repo: TraceRepository) -> None:
    created = await repo.create(_new(status=TraceStatus.RUNNING))
    finished = STARTED + timedelta(seconds=3)

    updated = await repo.update(
        created.id,
        TraceUpdate(
            status=TraceStatus.SUCCEEDED,
            finished_at=finished,
            schema_version="0.1.0",
            payload={"steps": []},
        ),
    )

    assert updated is not None
    assert updated.status is TraceStatus.SUCCEEDED
    assert updated.finished_at == finished
    assert updated.schema_version == "0.1.0"
    assert updated.payload == {"steps": []}
    assert updated.odoo_version is None
    assert updated.error is None


async def test_update_can_set_fields_to_null(repo: TraceRepository) -> None:
    created = await repo.create(_new())
    await repo.update(created.id, TraceUpdate(error="boom"))

    updated = await repo.update(created.id, TraceUpdate(error=None))

    assert updated is not None
    assert updated.error is None


async def test_update_unknown_id_returns_none(repo: TraceRepository) -> None:
    assert await repo.update(uuid.uuid4(), TraceUpdate(error="x")) is None


async def test_delete(repo: TraceRepository) -> None:
    created = await repo.create(_new())

    assert await repo.delete(created.id) is True
    assert await repo.get(created.id) is None
    assert await repo.delete(created.id) is False


async def test_list_by_filters_orders_and_pages(
    repo: TraceRepository, db_session: AsyncSession
) -> None:
    confirm_a = await repo.create(_new())
    confirm_b = await repo.create(_new(status=TraceStatus.FAILED))
    invoice = await repo.create(_new("account.move", "action_post"))
    # created_at comes from now() (same value inside one transaction), so pin it.
    for offset, trace in enumerate([confirm_a, confirm_b, invoice]):
        trace.created_at = STARTED + timedelta(minutes=offset)
    await db_session.flush()

    everything = await repo.list_by(TraceFilter(), limit=10)
    assert [t.id for t in everything] == [invoice.id, confirm_b.id, confirm_a.id]

    by_entrypoint = await repo.list_by(
        TraceFilter(entrypoint_model="sale.order", entrypoint_method="action_confirm"), limit=10
    )
    assert [t.id for t in by_entrypoint] == [confirm_b.id, confirm_a.id]

    failed = await repo.list_by(TraceFilter(status=TraceStatus.FAILED), limit=10)
    assert [t.id for t in failed] == [confirm_b.id]

    second_page = await repo.list_by(TraceFilter(), limit=1, offset=1)
    assert [t.id for t in second_page] == [confirm_b.id]


async def test_count_respects_filters(repo: TraceRepository) -> None:
    await repo.create(_new())
    await repo.create(_new(status=TraceStatus.FAILED))
    await repo.create(_new("account.move", "action_post"))

    assert await repo.count(TraceFilter()) == 3
    assert await repo.count(TraceFilter(entrypoint_model="sale.order")) == 2
    assert await repo.count(TraceFilter(status=TraceStatus.FAILED)) == 1
    assert await repo.count(TraceFilter(entrypoint_model="res.partner")) == 0
