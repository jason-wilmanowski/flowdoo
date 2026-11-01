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


def test_find_steps_combines_filters() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")

    found = trace_view.find_steps(trace, model="sale.order", field="state")

    assert found["total"] >= 1
    assert all(step["call"].startswith("sale.order.") for step in found["steps"])
    assert all("state" in step["changed"] for step in found["steps"])


def test_find_steps_reports_the_total_beyond_the_limit() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")

    found = trace_view.find_steps(trace, limit=5)

    assert found["total"] == len(trace["steps"])
    assert len(found["steps"]) == 5


def test_find_steps_failed_only() -> None:
    found = trace_view.find_steps(load_fixture("trace-error"), failed_only=True)

    assert [step["id"] for step in found["steps"]] == ["s1"]


def test_step_detail_has_path_and_children() -> None:
    trace = load_fixture("trace-error")

    assert trace_view.step_detail(trace, "s2") == {
        "step": trace["steps"][1],
        "path": ["s1 sale.order.action_confirm"],
        "children_total": 0,
        "children": [],
    }
    root = trace_view.step_detail(trace, "s1")
    assert root is not None
    assert root["path"] == []
    assert root["children"] == ["s2 sale.order._confirmation_error_message"]


def test_step_detail_of_an_unknown_step() -> None:
    assert trace_view.step_detail(load_fixture("trace-error"), "nope") is None
