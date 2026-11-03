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


def change(record_id: int, old: Any, new: Any) -> dict[str, Any]:
    return {"model": "stock.move", "record_id": record_id, "field": "qty", "old": old, "new": new}


def overview_with_changes(*changes: dict[str, Any]) -> dict[str, Any]:
    trace = load_fixture("trace-small")
    trace["steps"] = trace["steps"][:1]
    trace["steps"][0]["changes"] = list(changes)
    return trace_view.overview(trace)


def test_changed_field_of_one_record_shows_its_first_and_last_value() -> None:
    overview = overview_with_changes(change(1, 0, 1), change(1, 1, 2))

    assert overview["changed_fields"][0].startswith("stock.move.qty: 0 -> 2 (2x, first in s")


def test_changed_field_of_several_records_shows_each_different_transition() -> None:
    overview = overview_with_changes(change(1, 0, 38), change(2, 0, 6), change(3, 0, 5))

    line = overview["changed_fields"][0]

    assert line.startswith("stock.move.qty: 0 -> 38, 0 -> 6, 0 -> 5 (3 records, 3x, ")


def test_changed_field_of_several_records_merges_equal_transitions() -> None:
    overview = overview_with_changes(change(1, "a", "b"), change(2, "a", "b"))

    assert overview["changed_fields"][0].startswith("stock.move.qty: 'a' -> 'b' (2 records, 2x, ")


def test_changed_field_lists_a_few_transitions_and_says_how_many_more() -> None:
    overview = overview_with_changes(*(change(number, 0, number) for number in range(1, 6)))

    line = overview["changed_fields"][0]

    assert "0 -> 3, +2 more (5 records, 5x, " in line
    assert "0 -> 4" not in line


def test_changed_fields_stay_within_the_size_limit_and_report_the_total() -> None:
    wide = [
        {"model": "m", "record_id": record, "field": f"f{field}", "old": "x" * 80, "new": record}
        for field in range(90)
        for record in range(1, 4)
    ]

    overview = overview_with_changes(*wide)

    assert overview["changed_fields_total"] == 90
    assert 0 < len(overview["changed_fields"]) < 90
    assert answer_size(overview) < trace_view.MAX_ANSWER_CHARS + 2000


def test_overview_reports_the_total_of_cut_lists() -> None:
    trace = load_fixture("trace-small")
    root = trace["steps"][0]
    error = {"type": "ValueError", "message": "x"}
    children = [
        {**root, "id": f"c{number}", "parent_id": root["id"], "seq": 100 + number, "error": error}
        for number in range(trace_view.MAX_LISTED_CALLS + 5)
    ]
    trace["steps"] = [root, *children]

    overview = trace_view.overview(trace)

    assert overview["top_level_calls_total"] == trace_view.MAX_LISTED_CALLS + 6
    assert len(overview["top_level_calls"]) == trace_view.MAX_LISTED_CALLS
    assert overview["failures_total"] == trace_view.MAX_LISTED_CALLS + 5
    assert len(overview["failures"]) == trace_view.MAX_LISTED_FAILURES


def test_overview_shows_warnings_kept_with_the_trace() -> None:
    trace = load_fixture("trace-small")
    assert "warnings" not in trace_view.overview(trace)

    assert trace_view.overview({**trace, "warnings": ["careful"]})["warnings"] == ["careful"]


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
    assert step["mro_position"] is not None
    assert step["args"]


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
        {"mro_position": 0, "module": "sale", "calls_super": False, "step": "s1"}
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


def changing_steps() -> dict[str, Any]:
    """action_confirm > _apply_rules > write (mail) > write (ORM, which changes the value)."""
    trace = load_fixture("trace-small")
    template = trace["steps"][0]
    blank = {**template, "changes": [], "error": None, "record_ids": [1], "duration_ms": 1}

    def step(number: int, parent: str | None, kind: str, method: str, module: str | None) -> Any:
        return {
            **blank,
            "id": f"s{number}",
            "seq": number,
            "parent_id": parent,
            "kind": kind,
            "model": "sale.order",
            "method": method,
            "module": module,
        }

    steps = [
        step(1, None, "method_call", "action_confirm", "sale"),
        step(2, "s1", "method_call", "_apply_rules", "custom"),
        step(3, "s2", "orm_write", "write", "mail"),
        step(4, "s3", "orm_write", "write", None),
        step(5, "s1", "method_call", "_other", "sale"),
    ]
    steps[3]["changes"] = [
        {"model": "sale.order", "record_id": 1, "field": "policy", "old": "a", "new": "b"}
    ]
    return {**trace, "steps": steps}


def test_a_change_names_the_business_method_above_the_write_chain() -> None:
    overview = trace_view.overview(changing_steps())

    assert "by sale.order._apply_rules [custom]" in overview["changed_fields"][0]


def test_explain_field_gives_the_change_its_method_and_path() -> None:
    answer = trace_view.explain_field(changing_steps(), "policy")

    change = answer["changes"][0]
    assert answer["changes_total"] == 1
    assert (change["step"], change["old"], change["new"]) == ("s4", "a", "b")
    assert change["by"] == "sale.order._apply_rules [custom]"
    assert change["path"][1].startswith("s2 method_call sale.order._apply_rules")


def test_explain_field_filters_by_record_and_model() -> None:
    assert trace_view.explain_field(changing_steps(), "policy", record_id=2)["changes"] == []
    assert trace_view.explain_field(changing_steps(), "policy", model="x")["changes"] == []
    assert trace_view.explain_field(changing_steps(), "policy", record_id=1)["changes"]


def test_explain_field_without_a_change_warns_about_direct_sql() -> None:
    answer = trace_view.explain_field(changing_steps(), "credit_state")

    assert answer["changes_total"] == 0
    assert "direct SQL" in answer["hint"]


def test_fields_only_filled_on_new_records_become_one_line_per_model() -> None:
    new = [{"model": "m", "record_id": 1, "field": name, "old": None, "new": 1} for name in "ab"]
    trace = changing_steps()
    trace["steps"][2]["changes"] = new

    overview = trace_view.overview(trace)

    assert overview["filled_fields"] == ["m: a, b"]
    assert overview["changed_fields_total"] == 3
    assert len(overview["changed_fields"]) == 1


def test_find_steps_stays_within_a_subtree() -> None:
    found = trace_view.find_steps(changing_steps(), under="s2")

    assert [step["id"] for step in found["steps"]] == ["s2", "s3", "s4"]


def test_find_steps_excludes_modules_and_finds_a_record() -> None:
    trace = changing_steps()

    kept = trace_view.find_steps(trace, exclude_modules=["mail", "sale"])
    other = trace_view.find_steps(trace, record_id=99)

    assert [step["id"] for step in kept["steps"]] == ["s2", "s4"]
    assert other["total"] == 0


def test_a_short_step_leaves_out_empty_values() -> None:
    step = trace_view.find_steps(changing_steps(), method="_other")["steps"][0]

    assert "changes" not in step
    assert "error" not in step
    assert "calls_super" not in step
    assert "duration_ms" not in step
    assert step["module"] == "sale"


def test_the_orm_write_is_shown_as_base() -> None:
    step = trace_view.find_steps(changing_steps(), field="policy")["steps"][0]

    assert step["module"] == "base"


def test_huge_input_is_cut_in_the_overview() -> None:
    trace = load_fixture("trace-small")
    trace["entrypoint"]["kwargs"] = {"vals_list": [{"name": "x" * 100}] * 1000}

    overview = trace_view.overview(trace)

    assert len(overview["kwargs"]) < 400
    assert answer_size(overview) < trace_view.MAX_ANSWER_CHARS


def test_a_cut_recording_is_no_failure() -> None:
    trace = load_fixture("trace-small")
    trace["error"] = {"type": trace_view.TRUNCATED_ERROR, "message": "Stopped after 20000 steps"}

    overview = trace_view.overview(trace)

    assert overview["error"] is None
    assert "20000" in overview["recording_truncated"]


def test_noise_is_left_out_of_the_top_level_calls() -> None:
    trace = changing_steps()
    trace["steps"][4]["method"] = "_track_prepare"

    calls = trace_view.overview(trace)["top_level_calls"]

    assert not any("_track_prepare" in call for call in calls)


def test_long_lists_of_counts_are_summed_up() -> None:
    assert trace_view._counts(str(number) for number in range(12))["(others)"] == 2


def test_list_summary_tells_apart_runs_of_one_method() -> None:
    trace = load_fixture("trace-small")
    trace["entrypoint"]["kwargs"] = {"a": 1}

    assert '"a": 1' in trace_view.summary(trace)["kwargs"]


def compared(**change: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    first, second = changing_steps(), changing_steps()
    second["steps"] = second["steps"][:2] + second["steps"][4:]
    return first, second


def test_compare_finds_the_first_different_step_with_its_path() -> None:
    first, second = compared()

    answer = trace_view.compare_traces(first, second)

    assert answer["same_steps"] is False
    assert answer["first_difference"]["a"]["step"].startswith("s3 orm_write sale.order.write")
    assert answer["first_difference"]["a"]["path"][-1].startswith("s2 method_call")
    assert answer["first_difference"]["b"] is None
    assert answer["only_in_a"] == {"sale.order.write": 2}
    assert answer["only_in_b"] == {}


def test_compare_shows_values_that_differ_and_ignores_generated_ones() -> None:
    first, second = changing_steps(), changing_steps()
    second["steps"][3]["changes"] = [{**first["steps"][3]["changes"][0], "new": "c"}]
    extra = {"model": "m", "record_id": 1, "field": "name", "old": None}
    first["steps"][4]["changes"] = [{**extra, "new": "x"}]
    second["steps"][4]["changes"] = [{**extra, "new": "y"}]

    answer = trace_view.compare_traces(first, second)

    assert answer["same_steps"] is True
    assert answer["different_values"] == ["sale.order.policy: a 'b' (s4), b 'c' (s4)"]


def test_compare_reports_direct_sql_of_one_run() -> None:
    first, second = changing_steps(), changing_steps()
    first["raw_sql_writes"] = [
        {
            "operation": "UPDATE",
            "table": "t",
            "columns": ["c"],
            "method": "m",
            "file": "f.py",
            "line": 1,
        }
    ]

    answer = trace_view.compare_traces(first, second)

    assert answer["raw_sql_only_in_a"] == ["UPDATE t c by m at f.py:1"]
    assert answer["raw_sql_only_in_b"] == []


def test_compare_of_very_long_runs_stays_cheap() -> None:
    first, second = changing_steps(), changing_steps()
    first["steps"] = [
        {**first["steps"][0], "id": f"x{n}", "seq": n}
        for n in range(trace_view.MAX_COMPARED_STEPS + 1)
    ]

    assert "note" in trace_view.compare_traces(first, second)


def test_a_path_shows_a_chain_of_overrides_once() -> None:
    trace = changing_steps()
    trace["steps"][1]["method"] = "action_confirm"

    path = trace_view.explain_field(trace, "policy")["changes"][0]["path"]

    assert [line.split()[0] for line in path] == ["s1", "s3"]
