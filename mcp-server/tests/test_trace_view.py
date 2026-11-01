from conftest import load_fixture

from flowdoo_mcp import trace_view


def test_overview_of_a_recorded_trace_is_small() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")

    overview = trace_view.overview(trace)

    assert overview["entrypoint"] == "sale.order.action_confirm"
    assert overview["step_count"] == len(trace["steps"])
    assert "sale.order" in overview["models"]
    assert "sale" in overview["modules"]
    assert "sale.order.state" in overview["changed_fields"]
    assert len(str(overview)) < len(str(trace)) / 10


def test_overview_names_the_failed_steps() -> None:
    overview = trace_view.overview(load_fixture("trace-error"))

    assert overview["failed_steps"] == ["s1"]
    assert overview["error"]["type"] == "odoo.exceptions.UserError"


def test_find_steps_without_filters_returns_nothing() -> None:
    found = trace_view.find_steps(load_fixture("trace-small"))

    assert found == {"steps_total": 0, "steps": []}


def test_find_steps_combines_filters() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")

    found = trace_view.find_steps(trace, model="sale.order", field="state")

    assert found["steps_total"] >= 1
    for step in found["steps"]:
        assert step["model"] == "sale.order"
        assert "state" in {change["field"] for change in step["changes"]}


def test_find_steps_reports_the_total_beyond_the_limit() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")

    found = trace_view.find_steps(trace, model="sale.order", limit=2)

    assert found["steps_total"] > 2
    assert len(found["steps"]) == 2


def test_find_steps_failed_only() -> None:
    found = trace_view.find_steps(load_fixture("trace-error"), failed_only=True)

    assert [step["id"] for step in found["steps"]] == ["s1"]
