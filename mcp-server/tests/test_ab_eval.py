from pathlib import Path

import ab_eval
import pytest

MCP = Path("/tmp/mcp.json")


def task(name: str = "t") -> ab_eval.Task:
    return {"id": name, "category": "flow", "prompt": "Why?", "rubric": ["one", "two"]}


def row(run_id: str, task_id: str, arm: str, *, tokens: int = 10) -> dict[str, object]:
    metrics = {
        "fresh_input_tokens": tokens,
        "total_input_tokens": tokens,
        "output_tokens": 1,
        "cost_usd": 0.1,
        "turns": 2,
        "duration_s": 3.0,
        "failed": False,
        "permission_denials": 0,
    }
    return {"run_id": run_id, "task": task_id, "arm": arm, "metrics": metrics, "answer": "text"}


def build(arm: str) -> list[str]:
    run = ab_eval.Run("t", arm, 0)
    return ab_eval.command(run, task(), model="sonnet", budget=1.0, db="dev", mcp=MCP)


def test_tasks_are_complete_and_cover_the_control_case() -> None:
    tasks = ab_eval.load_tasks()

    assert len({item["id"] for item in tasks}) == len(tasks) >= 5
    assert all(item["prompt"] and item["rubric"] for item in tasks)
    assert {"flow", "control", "branches"} <= {item["category"] for item in tasks}


def test_prompts_do_not_name_the_tool_under_test() -> None:
    for item in ab_eval.load_tasks():
        assert "flowdoo" not in item["prompt"].lower()
    assert "flowdoo" not in ab_eval.SYSTEM_PROMPT.lower()


def test_schedule_runs_every_task_in_both_arms_in_a_stable_shuffled_order() -> None:
    tasks = [task("a"), task("b")]

    runs = ab_eval.schedule(tasks, reps=3, seed=1)

    assert len(runs) == len({run.run_id for run in runs}) == 12
    assert runs == ab_eval.schedule(tasks, reps=3, seed=1)
    assert runs != sorted(runs, key=lambda run: run.run_id)


def test_arms_differ_only_in_the_mcp_server() -> None:
    baseline, flowdoo = build("baseline"), build("flowdoo")

    assert "--mcp-config" not in baseline
    assert flowdoo[flowdoo.index("--mcp-config") + 1] == str(MCP)
    assert "--strict-mcp-config" in baseline
    assert "--strict-mcp-config" in flowdoo
    assert baseline[baseline.index("--tools") + 1] == flowdoo[flowdoo.index("--tools") + 1]
    assert "mcp__flowdoo" not in baseline[baseline.index("--allowedTools") + 1]
    assert "mcp__flowdoo" in flowdoo[flowdoo.index("--allowedTools") + 1]


def test_metrics_read_the_cli_result() -> None:
    result = {
        "usage": {
            "input_tokens": 2,
            "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": 100,
            "output_tokens": 5,
        },
        "total_cost_usd": 0.5,
        "num_turns": 4,
        "duration_ms": 1500,
        "is_error": False,
        "permission_denials": [{}],
    }

    assert ab_eval.metrics(result) == {
        "fresh_input_tokens": 12,
        "total_input_tokens": 112,
        "output_tokens": 5,
        "cost_usd": 0.5,
        "turns": 4,
        "duration_s": 1.5,
        "failed": False,
        "permission_denials": 1,
    }


def test_redact_hides_what_gives_the_arm_away() -> None:
    text = "Flowdoo trace s12 via mcp__flowdoo__get_step in sale_stock, see sale.order"

    redacted = ab_eval.redact(text)

    assert "[step]" in redacted
    for hint in ("Flowdoo", "s12", "mcp__", "trace"):
        assert hint not in redacted
    assert "sale_stock" in redacted
    assert "sale.order" in redacted


def test_blind_sheet_hides_the_arm_and_keeps_the_key_apart() -> None:
    rows = [row("t-flowdoo-0", "t", "flowdoo"), row("t-baseline-0", "t", "baseline")]

    sheet, key, grades = ab_eval.blind_sheet(rows, [task()], seed=1)

    assert "flowdoo" not in sheet
    assert "baseline" not in sheet
    assert set(key.values()) == {"t-flowdoo-0", "t-baseline-0"}
    assert grades["a001"] == {"one": None, "two": None}


def test_scores_skip_answers_that_are_not_fully_graded() -> None:
    key = {"a001": "done", "a002": "open"}
    grades = {"a001": {"x": True, "y": False}, "a002": {"x": True, "y": None}}

    assert ab_eval.scores(key, grades) == {"done": pytest.approx(0.5)}


def test_summary_gives_medians_per_task_and_arm() -> None:
    rows = [
        row("t-flowdoo-0", "t", "flowdoo", tokens=10),
        row("t-flowdoo-1", "t", "flowdoo", tokens=20),
        row("t-flowdoo-2", "t", "flowdoo", tokens=900),
        row("t-baseline-0", "t", "baseline", tokens=50),
    ]

    baseline, flowdoo = ab_eval.summarize(rows, {"t-flowdoo-0": 1.0})

    assert (baseline["arm"], flowdoo["arm"]) == ("baseline", "flowdoo")
    assert flowdoo["n"] == 3
    assert flowdoo["total_input_tokens"] == 20
    assert flowdoo["score"] == 1.0
    assert baseline["score"] is None


def test_markdown_table_has_a_row_per_line() -> None:
    table = ab_eval.markdown_table([{"task": "t", "n": 1}])

    assert table.splitlines()[0] == "| task | n |"
    assert table.splitlines()[-1] == "| t | 1 |"
