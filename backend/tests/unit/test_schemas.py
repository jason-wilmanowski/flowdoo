import pytest
from pydantic import ValidationError

from flow_tracer_api.schemas import StartTraceCommand, TraceListQuery


def test_start_trace_defaults_to_dry_run() -> None:
    command = StartTraceCommand(entrypoint_model=" sale.order ", entrypoint_method="action_confirm")

    assert command.dry_run is True
    assert command.entrypoint_model == "sale.order"
    assert command.record_ids == ()
    assert command.context == {}


@pytest.mark.parametrize("field", ["entrypoint_model", "entrypoint_method"])
@pytest.mark.parametrize("value", ["", "   ", "x" * 129])
def test_start_trace_rejects_bad_entrypoint(field: str, value: str) -> None:
    data = {"entrypoint_model": "sale.order", "entrypoint_method": "action_confirm", field: value}

    with pytest.raises(ValidationError):
        StartTraceCommand.model_validate(data)


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (201, 0), (10, -1)])
def test_list_query_bounds(limit: int, offset: int) -> None:
    with pytest.raises(ValidationError):
        TraceListQuery(limit=limit, offset=offset)
