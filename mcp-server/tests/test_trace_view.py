import json
from typing import Any

from conftest import load_fixture

from flowdoo_mcp import trace_view


def answer_size(answer: dict[str, Any]) -> int:
    return len(json.dumps(answer, indent=2))


def test_overview_of_a_recorded_trace_says_what_happened_and_is_small() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")

    overview = trace_view.overview(trace)

    assert overview["entrypoint"] == "sale.order.action_confirm"
    assert overview["step_count"] == len(trace["steps"])
    assert overview["models"]["sale.order"] > 0
    assert overview["modules"]["sale"] > 0
    assert any(
        line.startswith("sale.order.state: 'draft' -> 'sale'")
        for line in overview["changed_fields"]
    )
    assert overview["top_level_calls"][0].startswith("s1 method_call sale.order.action_confirm")
    assert answer_size(overview) < trace_view.MAX_ANSWER_CHARS


def test_overview_points_to_where_a_failure_starts() -> None:
    overview = trace_view.overview(load_fixture("trace-error"))

    assert overview["failed_total"] == 1
    assert overview["failures"][0]["step"] == "s1"
    assert overview["failures"][0]["error"]["type"] == "odoo.exceptions.UserError"
    assert overview["error"]["type"] == "odoo.exceptions.UserError"


def test_failure_origin_is_the_deepest_failed_step() -> None:
    trace = load_fixture("trace-error")
    trace["steps"][1]["error"] = trace["steps"][0]["error"]

    origin = trace_view.overview(trace)["failures"][0]

    assert origin["step"] == "s2"
    assert origin["path"][0].startswith("s1 ")


def test_find_steps_combines_filters_and_shows_details() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")

    found = trace_view.find_steps(trace, model="sale.order", field="state")

    assert found["total"] >= 1
    step = found["steps"][0]
    assert step["call"] == "sale.order.write"
    assert any("state: 'draft' -> 'sale'" in change for change in step["changes"])
    assert {"mro_position", "calls_super", "args", "returns", "duration_ms"} <= step.keys()


def test_find_steps_pages_through_all_steps_within_the_size_limit() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")
    seen: list[str] = []
    offset: int | None = 0

    while offset is not None:
        page = trace_view.find_steps(trace, limit=100, offset=offset)
        assert answer_size(page) < trace_view.MAX_ANSWER_CHARS
        seen += [step["id"] for step in page["steps"]]
        offset = page["next_offset"]

    assert len(seen) == len(set(seen)) == len(trace["steps"])


def test_find_steps_failed_only() -> None:
    found = trace_view.find_steps(load_fixture("trace-error"), failed_only=True)

    assert [step["id"] for step in found["steps"]] == ["s1"]


def test_long_values_are_cut_and_say_so() -> None:
    trace = load_fixture("trace-error")
    trace["steps"][0]["args_summary"] = "x" * 1000

    step = trace_view.find_steps(trace, failed_only=True)["steps"][0]

    assert step["args"].startswith("xxx")
    assert "800 more characters, see get_step" in step["args"]


def test_step_detail_has_the_full_step_path_children_and_implementations() -> None:
    trace = load_fixture("trace-error")

    leaf = trace_view.step_detail(trace, "s2")
    root = trace_view.step_detail(trace, "s1")

    assert leaf is not None
    assert root is not None
    assert leaf["step"] == trace["steps"][1]
    assert leaf["path"][0].startswith("s1 method_call sale.order.action_confirm")
    assert root["path"] == []
    assert root["children"][0].startswith("s2 method_call sale.order._confirmation_error_message")
    assert root["implementations_seen"] == [
        {"mro_position": 0, "module": "sale", "calls_super": False}
    ]


def test_step_detail_of_the_largest_recorded_step_fits() -> None:
    trace = load_fixture("recorded-sale-order-action-confirm")
    largest = max(trace["steps"], key=lambda step: len(step["changes"]))

    detail = trace_view.step_detail(trace, largest["id"])

    assert detail is not None
    assert detail["changes_total"] == len(detail["step"]["changes"]) == len(largest["changes"])
    assert answer_size(detail) < trace_view.MAX_ANSWER_CHARS


def test_step_detail_cuts_huge_changes_and_reports_the_total() -> None:
    trace = load_fixture("trace-error")
    change = {
        "model": "sale.order",
        "record_id": 3,
        "field": "note",
        "old": None,
        "new": "x" * 2000,
    }
    trace["steps"][0]["changes"] = [change] * 100

    detail = trace_view.step_detail(trace, "s1")

    assert detail is not None
    assert detail["changes_total"] == 100
    assert 0 < len(detail["step"]["changes"]) < 100
    assert answer_size(detail) < trace_view.MAX_ANSWER_CHARS + 1000


def test_step_detail_of_an_unknown_step() -> None:
    assert trace_view.step_detail(load_fixture("trace-error"), "nope") is None


def test_a_cycle_in_the_step_tree_does_not_hang() -> None:
    trace = load_fixture("trace-error")
    trace["steps"][0]["parent_id"] = "s2"

    assert trace_view.step_detail(trace, "s2") is not None
