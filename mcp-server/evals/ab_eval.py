"""Compare a headless Claude Code with and without the Flowdoo MCP server.

Both arms get the same prompt, Odoo source and odoo shell; only the MCP server differs.
Answers are graded blind against a rubric that was fixed before the first run.
See README.md for the procedure.
"""

import argparse
import json
import random
import re
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MCP_DIR = HERE.parent
RESULTS = HERE / "results"
ARMS = ("baseline", "flowdoo")
ODOO_CONTAINER = "flow-tracer-odoo-test-1"
ODOO_SOURCE = "/usr/lib/python3/dist-packages/odoo"
SHELL_PREFIX = f"docker exec -i {ODOO_CONTAINER} /entrypoint.sh odoo shell"
RUN_TIMEOUT_SECONDS = 900

SYSTEM_PROMPT = """\
You are helping a developer on an Odoo 19 server. A read-only copy of its source is in ./odoo.
The server's database is {db}, a neutralised development database with demo data. Order id 1
is a draft sale order. To run Python on the server, pipe a script into:
  {shell} -d {db} --no-http --log-level=warn
The script gets `env`. Start it with `env = env(user=env.ref('base.user_admin'))` and end it
with `env.cr.rollback()`. Never commit. Answer concisely and say what your answer is based on.
"""

Task = dict[str, Any]


@dataclass(frozen=True)
class Run:
    task: str
    arm: str
    rep: int

    @property
    def run_id(self) -> str:
        return f"{self.task}-{self.arm}-{self.rep}"


def load_tasks() -> list[Task]:
    tasks: list[Task] = json.loads((HERE / "tasks.json").read_text())
    return tasks


def schedule(tasks: list[Task], reps: int, seed: int) -> list[Run]:
    """Every task in both arms, in random order so drift does not favour one arm."""
    runs = [Run(task["id"], arm, rep) for task in tasks for arm in ARMS for rep in range(reps)]
    random.Random(seed).shuffle(runs)
    return runs


def command(run: Run, task: Task, *, model: str, budget: float, db: str, mcp: Path) -> list[str]:
    allowed = ["Read", "Grep", "Glob", f"Bash({SHELL_PREFIX}:*)"]
    servers = ["--strict-mcp-config"]
    if run.arm == "flowdoo":
        allowed.append("mcp__flowdoo")
        servers += ["--mcp-config", str(mcp)]
    return [
        "claude",
        "-p",
        task["prompt"],
        "--output-format",
        "json",
        "--model",
        model,
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--max-budget-usd",
        str(budget),
        "--tools",
        "Read,Grep,Glob,Bash",
        "--allowedTools",
        ",".join(allowed),
        "--append-system-prompt",
        SYSTEM_PROMPT.format(db=db, shell=SHELL_PREFIX),
        *servers,
    ]


def metrics(result: dict[str, Any]) -> dict[str, Any]:
    usage = result.get("usage", {})
    fresh = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
    return {
        "fresh_input_tokens": fresh,
        "total_input_tokens": fresh + usage.get("cache_read_input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": result.get("total_cost_usd", 0),
        "turns": result.get("num_turns", 0),
        "duration_s": round(result.get("duration_ms", 0) / 1000, 1),
        "failed": bool(result.get("is_error")),
        "permission_denials": len(result.get("permission_denials", [])),
    }


def redact(answer: str) -> str:
    """Hide what gives the arm away. Only partly possible: answers also differ in style."""
    answer = re.sub(r"\bs\d+\b", "[step]", answer)
    return re.sub(r"mcp__\S+|flowdoo|flow_tracer|\btrace[sd]?\b", "[source]", answer, flags=re.I)


def blind_sheet(rows: list[dict[str, Any]], tasks: list[Task], seed: int) -> tuple[str, dict, dict]:
    """The sheet to grade, the key from answer id to run, and an empty grades file."""
    rubrics = {task["id"]: task["rubric"] for task in tasks}
    shuffled = rows[:]
    random.Random(seed).shuffle(shuffled)
    shuffled.sort(key=lambda row: row["task"])
    sheet, key, grades = ["# Grading sheet\n"], {}, {}
    for number, row in enumerate(shuffled, start=1):
        answer_id = f"a{number:03}"
        key[answer_id] = row["run_id"]
        grades[answer_id] = {criterion: None for criterion in rubrics[row["task"]]}
        sheet += [f"## {answer_id} ({row['task']})\n", redact(row["answer"]), "\n"]
    return "\n".join(sheet), key, grades


def scores(key: dict[str, str], grades: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Share of met criteria per run; an answer not graded completely yet has no score."""
    result = {}
    for answer_id, marks in grades.items():
        if marks and all(mark is not None for mark in marks.values()):
            result[key[answer_id]] = sum(bool(mark) for mark in marks.values()) / len(marks)
    return result


def summarize(rows: list[dict[str, Any]], run_scores: dict[str, float]) -> list[dict[str, Any]]:
    """Medians per task and arm; with few repetitions medians hold up best against outliers."""
    summary = []
    for task, arm in sorted({(row["task"], row["arm"]) for row in rows}):
        group = [row for row in rows if row["task"] == task and row["arm"] == arm]
        graded = [run_scores[row["run_id"]] for row in group if row["run_id"] in run_scores]
        line: dict[str, Any] = {"task": task, "arm": arm, "n": len(group)}
        for name in ("fresh_input_tokens", "total_input_tokens", "output_tokens", "cost_usd"):
            line[name] = statistics.median(row["metrics"][name] for row in group)
        for name in ("turns", "duration_s"):
            line[name] = statistics.median(row["metrics"][name] for row in group)
        line["failed"] = sum(row["metrics"]["failed"] for row in group)
        line["score"] = round(statistics.median(graded), 2) if graded else None
        summary.append(line)
    return summary


def markdown_table(summary: list[dict[str, Any]]) -> str:
    columns = list(summary[0]) if summary else []
    lines = ["| " + " | ".join(columns) + " |", "|" + " --- |" * len(columns)]
    lines += ["| " + " | ".join(str(line[name]) for name in columns) + " |" for line in summary]
    return "\n".join(lines)


def database_name() -> str:
    for line in (MCP_DIR / ".env").read_text().splitlines():
        if line.startswith("ODOO_DB="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("ODOO_DB is missing in mcp-server/.env")


def write_mcp_config(workspace: Path) -> Path:
    server = {"command": "uv", "args": ["run", "--directory", str(MCP_DIR), "flowdoo-mcp"]}
    path = workspace / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"flowdoo": server}}))
    return path


def prepare(args: argparse.Namespace) -> None:
    """A folder outside the repo, so neither arm sees the Flowdoo code or its instructions."""
    args.workspace.mkdir(parents=True, exist_ok=True)
    if not (args.workspace / "odoo").exists():
        source = f"{ODOO_CONTAINER}:{ODOO_SOURCE}"
        subprocess.run(["docker", "cp", "-L", source, str(args.workspace / "odoo")], check=True)
    write_mcp_config(args.workspace)
    print(f"Workspace ready: {args.workspace}")


def run_all(args: argparse.Namespace) -> None:
    tasks = {task["id"]: task for task in load_tasks()}
    selected = [tasks[name] for name in args.tasks] if args.tasks else list(tasks.values())
    runs = schedule(selected, args.reps, args.seed)
    print(f"{len(runs)} runs, at most ${args.budget} each, ${len(runs) * args.budget} in total")
    if args.dry_run:
        for run in runs:
            print(run.run_id)
        return
    RESULTS.mkdir(exist_ok=True)
    db = database_name()
    mcp = write_mcp_config(args.workspace)
    for run in runs:
        target = RESULTS / f"{run.run_id}.json"
        if target.exists():
            continue
        call = command(run, tasks[run.task], model=args.model, budget=args.budget, db=db, mcp=mcp)
        _record(run, call, target, args)


def _record(run: Run, call: list[str], target: Path, args: argparse.Namespace) -> None:
    done = subprocess.run(
        call,
        cwd=args.workspace,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=RUN_TIMEOUT_SECONDS,
        check=False,
    )
    try:
        result = json.loads(done.stdout)
    except json.JSONDecodeError:
        print(f"{run.run_id}: no answer: {done.stderr[:300]}", file=sys.stderr)
        return
    row = {
        "run_id": run.run_id,
        "task": run.task,
        "arm": run.arm,
        "rep": run.rep,
        "model": args.model,
        "metrics": metrics(result),
        "answer": result.get("result", ""),
    }
    target.write_text(json.dumps(row, indent=1))
    print(run.run_id, row["metrics"], flush=True)


def load_rows() -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in sorted(RESULTS.glob("*-*-*.json"))]


def sheet(args: argparse.Namespace) -> None:
    text, key, grades = blind_sheet(load_rows(), load_tasks(), args.seed)
    (RESULTS / "grading_sheet.md").write_text(text)
    (RESULTS / "blind.key").write_text(json.dumps(key, indent=1))
    (RESULTS / "grades.todo").write_text(json.dumps(grades, indent=1))
    print(f"Grade {RESULTS / 'grading_sheet.md'} in {RESULTS / 'grades.todo'} (true or false)")


def report(_: argparse.Namespace) -> None:
    key_path, grades_path = RESULTS / "blind.key", RESULTS / "grades.todo"
    run_scores: dict[str, float] = {}
    if key_path.exists() and grades_path.exists():
        run_scores = scores(json.loads(key_path.read_text()), json.loads(grades_path.read_text()))
    print(markdown_table(summarize(load_rows(), run_scores)))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--workspace", type=Path, default=Path("/tmp/flowdoo-ab"))
    root.add_argument("--seed", type=int, default=20261101)
    steps = root.add_subparsers(required=True)
    steps.add_parser("prepare", help="copy the Odoo source").set_defaults(step=prepare)
    run = steps.add_parser("run", help="run the tasks; finished runs are kept")
    run.add_argument("--reps", type=int, default=3)
    run.add_argument("--model", default="sonnet")
    run.add_argument("--budget", type=float, default=2.0, help="USD limit per run")
    run.add_argument("--tasks", nargs="*", help="only these task ids")
    run.add_argument("--dry-run", action="store_true", help="only list the runs")
    run.set_defaults(step=run_all)
    steps.add_parser("sheet", help="write the blind grading sheet").set_defaults(step=sheet)
    steps.add_parser("report", help="print the results").set_defaults(step=report)
    return root


def main() -> None:
    shutil.which("claude") or sys.exit("The claude CLI is not on the PATH")
    args = parser().parse_args()
    args.step(args)


if __name__ == "__main__":
    main()
