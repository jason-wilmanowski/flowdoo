import { loadFixture } from "@/datasource/fixtures/catalog";
import type { Step } from "@/generated/trace";
import { indexTrace } from "@/lib/replay/traceIndex";

import { changesByRecord, changesOverTime, netChanges, subtreeSteps } from "./changes";
import { layoutLayers, modelGraph } from "./modelGraph";
import { ancestorsOf, collapseBelow, revealStep, visibleRows } from "./treeRows";
import { formatValue } from "./values";

const step = (
  id: string,
  parent: string | null,
  seq: number,
  model: string,
  extra: Partial<Step> = {},
): Step => ({
  id,
  parent_id: parent,
  seq,
  kind: "method_call",
  model,
  method: `m${id}`,
  module: "sale",
  mro_position: 0,
  calls_super: true,
  record_ids: [1],
  args_summary: null,
  return_summary: null,
  changes: [],
  duration_ms: 1,
  error: null,
  ...extra,
});

// s1 sale.order ─ s2 sale.order ─ s3 stock.picking
//               └ s4 account.move (writes two fields on two records)
const STEPS = [
  step("s1", null, 1, "sale.order"),
  step("s2", "s1", 2, "sale.order"),
  step("s3", "s2", 3, "stock.picking", { module: null }),
  step("s4", "s1", 4, "account.move", {
    changes: [
      { model: "account.move", record_id: 7, field: "state", old: "draft", new: "posted" },
      { model: "account.move", record_id: 8, field: "state", old: "draft", new: "posted" },
      { model: "account.move", record_id: 7, field: "line_ids", old: null, new: [1, 2] },
    ],
  }),
];
const index = indexTrace({ steps: STEPS });

describe("tree rows", () => {
  it("lists steps depth-first in seq order and hides collapsed children", () => {
    expect(visibleRows(index, new Set()).map((r) => [r.id, r.depth, r.parentId])).toEqual([
      ["s1", 0, null],
      ["s2", 1, "s1"],
      ["s3", 2, "s2"],
      ["s4", 1, "s1"],
    ]);
    expect(visibleRows(index, new Set(["s2"])).map((r) => r.id)).toEqual(["s1", "s2", "s4"]);
  });

  it("finds ancestors and reveals a hidden step", () => {
    expect(ancestorsOf(index, "s3")).toEqual(["s2", "s1"]);
    const revealed = revealStep(index, new Set(["s1", "s2", "s4"]), "s3");
    expect([...revealed]).toEqual(["s4"]);
  });

  it("collapses below a depth", () => {
    expect([...collapseBelow(index, 1)]).toEqual(["s2"]);
  });

  it("handles the recorded 879-step trace", async () => {
    const big = indexTrace(await loadFixture("recorded-sale-order-action-confirm"));
    expect(visibleRows(big, new Set())).toHaveLength(879);
    expect(visibleRows(big, collapseBelow(big, 2)).length).toBeLessThan(879);
  });
});

describe("changes", () => {
  it("lists changes in replay order and groups them by record", () => {
    expect(changesOverTime(index).map((c) => [c.step.id, c.position, c.change.field])).toEqual([
      ["s4", 3, "state"],
      ["s4", 3, "state"],
      ["s4", 3, "line_ids"],
    ]);
    expect(changesByRecord(STEPS[3]!).map((g) => [g.recordId, g.changes.length])).toEqual([
      [7, 2],
      [8, 1],
    ]);
  });

  it("formats values", () => {
    expect(formatValue(null)).toBe("null");
    expect(formatValue(false)).toBe("false");
    expect(formatValue(3.5)).toBe("3.5");
    expect(formatValue([1, 2])).toBe("[1, 2]");
    expect(formatValue("draft")).toBe("draft");
  });
});

describe("model graph", () => {
  it("counts calls and changes per model and draws calls across models", () => {
    const graph = modelGraph(index);
    expect(graph.nodes.map((n) => [n.model, n.calls, n.changes, n.layer, n.modules])).toEqual([
      ["sale.order", 2, 0, 0, ["sale"]],
      ["stock.picking", 1, 0, 1, ["core"]],
      ["account.move", 1, 3, 1, ["sale"]],
    ]);
    expect(graph.edges).toEqual([
      { source: "sale.order", target: "stock.picking", calls: 1 },
      { source: "sale.order", target: "account.move", calls: 1 },
    ]);
  });

  it("lays out layers as columns", () => {
    const positions = layoutLayers(modelGraph(index).nodes, { column: 300, row: 100 });
    expect(positions.get("sale.order")).toEqual({ x: 0, y: 0 });
    expect(positions.get("stock.picking")).toEqual({ x: 300, y: 0 });
    expect(positions.get("account.move")).toEqual({ x: 300, y: 100 });
  });

  it("builds the graph of the recorded trace", async () => {
    const graph = modelGraph(indexTrace(await loadFixture("recorded-sale-order-action-confirm")));
    expect(graph.nodes).toHaveLength(33);
    expect(graph.nodes[0]?.model).toBe("sale.order");
  });
});

describe("net changes of a call", () => {
  // s1 ─ s2 (create record 9: name) ─ s3 (write record 9: name, state)
  //    └ s4 (write record 9: state again)
  const calls = indexTrace({
    steps: [
      step("s1", null, 1, "sale.order"),
      step("s2", "s1", 2, "sale.order", {
        kind: "orm_create",
        changes: [{ model: "sale.order", record_id: 9, field: "name", old: null, new: "S9" }],
      }),
      step("s3", "s2", 3, "sale.order", {
        kind: "orm_write",
        changes: [
          { model: "sale.order", record_id: 9, field: "name", old: "S9", new: "S9a" },
          { model: "sale.order", record_id: 9, field: "state", old: "draft", new: "sent" },
        ],
      }),
      step("s4", "s1", 4, "sale.order", {
        kind: "orm_write",
        changes: [{ model: "sale.order", record_id: 9, field: "state", old: "sent", new: "sale" }],
      }),
    ],
  });

  it("collects the step and everything below it in order", () => {
    expect(subtreeSteps(calls, "s1").map((s) => s.id)).toEqual(["s1", "s2", "s3", "s4"]);
    expect(subtreeSteps(calls, "s2").map((s) => s.id)).toEqual(["s2", "s3"]);
  });

  it("reduces writes to the first old and the last new value per field", () => {
    expect(netChanges(calls, "s1")).toEqual([
      {
        model: "sale.order",
        recordId: 9,
        created: true,
        fields: [
          { field: "name", old: null, new: "S9a", writes: 2, lastStepId: "s3", lastPosition: 2 },
          {
            field: "state",
            old: "draft",
            new: "sale",
            writes: 2,
            lastStepId: "s4",
            lastPosition: 3,
          },
        ],
      },
    ]);
  });

  it("only sees what happened below the selected step", () => {
    const below = netChanges(calls, "s4");
    expect(below).toHaveLength(1);
    expect(below[0]?.created).toBe(false);
    expect(below[0]?.fields.map((f) => [f.field, f.old, f.new])).toEqual([
      ["state", "sent", "sale"],
    ]);
  });
});
