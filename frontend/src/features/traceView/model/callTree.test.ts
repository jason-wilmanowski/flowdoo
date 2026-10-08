import { loadFixture } from "@/datasource/fixtures/catalog";
import type { Step } from "@/generated/trace";
import { indexTrace } from "@/lib/replay/traceIndex";

import {
  buildCallTree,
  callPath,
  chainOfStep,
  expandAll,
  firstStepOfRow,
  isSuperCall,
  revealStep,
  rowForStep,
  visibleCallRows,
} from "./callTree";

const step = (
  id: string,
  parent: string | null,
  seq: number,
  model: string,
  method: string,
  extra: Partial<Step> = {},
): Step => ({
  id,
  parent_id: parent,
  seq,
  kind: "method_call",
  model,
  method,
  module: "sale",
  mro_position: 0,
  calls_super: false,
  record_ids: [1],
  args_summary: null,
  return_summary: null,
  changes: [],
  duration_ms: 1,
  error: null,
  ...extra,
});

const WRITE = { model: "sale.order.line", record_id: 2, field: "product_uom_qty", old: 5, new: 10 };

// w1 write (sale_stock) ─ w2 write (sale) ─ w3 write (core, changes qty)
//    └ h1 helper            └ h2 helper
// c1 compute ─ t1..t4 account.tax helpers (no changes), then c2 compute (changes)
const STEPS = [
  step("w1", null, 1, "sale.order.line", "write", { module: "sale_stock", calls_super: true }),
  step("h1", "w1", 2, "sale.order.line", "_update_line_quantity"),
  step("w2", "w1", 3, "sale.order.line", "write", { mro_position: 1, calls_super: true }),
  step("h2", "w2", 4, "sale.order.line", "_get_protected_fields"),
  step("w3", "w2", 5, "sale.order.line", "write", {
    module: null,
    mro_position: 2,
    kind: "orm_write",
    changes: [WRITE],
  }),
  step("c1", null, 6, "sale.order.line", "_compute_amount"),
  step("t1", "c1", 7, "account.tax", "_a"),
  step("t2", "c1", 8, "account.tax", "_b"),
  step("t3", "c1", 9, "account.tax", "_c"),
  step("t4", "c1", 10, "account.tax", "_d"),
  step("c2", "c1", 11, "sale.order", "_compute_amounts", {
    kind: "compute",
    changes: [{ model: "sale.order", record_id: 1, field: "amount_total", old: 1, new: 2 }],
  }),
];
const index = indexTrace({ steps: STEPS });
const tree = buildCallTree(index);
const ids = (rows: { id: string }[]) => rows.map((r) => r.id);

describe("super chains", () => {
  it("recognises the next implementation of the same call", () => {
    expect(isSuperCall(STEPS[0]!, STEPS[2]!)).toBe(true);
    expect(isSuperCall(STEPS[0]!, STEPS[1]!)).toBe(false);
  });

  it("makes one node per chain, with the calls of every layer as children", () => {
    const node = tree.nodes.get("w1")!;
    expect(node.chain.map((s) => s.id)).toEqual(["w1", "w2", "w3"]);
    expect(node.children).toEqual(["h1", "h2"]);
    expect(tree.nodes.get("h2")?.calledFrom?.id).toBe("w2");
    expect(tree.nodes.has("w2")).toBe(false);
    expect(chainOfStep(tree, "w3").map((s) => s.module)).toEqual(["sale_stock", "sale", null]);
    expect(node.ownChanges).toBe(1);
    expect(node.stepCount).toBe(5);
  });
});

describe("layers of a chain", () => {
  it("shows the implementations as a stack with the calls each one made", () => {
    expect(tree.display.get("w1")).toEqual(["layer:w1", "layer:w2", "layer:w3"]);
    expect(tree.display.get("layer:w1")).toEqual(["h1"]);
    expect(tree.display.get("layer:w2")).toEqual(["h2"]);
    expect(firstStepOfRow(tree, "layer:w2")).toBe("w2");
  });

  it("selects the layer row once the chain is open, and opens it on a jump", () => {
    expect(rowForStep(tree, new Set(), "w2")).toBe("w1");
    const revealed = revealStep(tree, new Set(), "w2");
    expect(rowForStep(tree, revealed, "w2")).toBe("layer:w2");
    expect(ids(visibleCallRows(tree, revealed)).slice(0, 4)).toEqual([
      "w1",
      "layer:w1",
      "layer:w2",
      "layer:w3",
    ]);
  });
});

describe("relevance and folding", () => {
  it("expands only paths to changes and folds irrelevant runs on one model", () => {
    const rows = visibleCallRows(tree, new Set());
    // w1 changed itself but has nothing relevant below: shown, not expanded
    // c1 has a relevant child (c2): expanded; t1..t4 folded into one group
    expect(ids(rows)).toEqual(["w1", "c1", "group:t1", "c2"]);
    const group = tree.groups.get("group:t1")!;
    expect(group.members).toEqual(["t1", "t2", "t3", "t4"]);
    expect(group.model).toBe("account.tax");
    expect(rows.find((r) => r.id === "w1")?.expanded).toBe(false);
  });

  it("finds the visible row for a hidden step and reveals it on request", () => {
    expect(rowForStep(tree, new Set(), "w2")).toBe("w1");
    expect(rowForStep(tree, new Set(), "t3")).toBe("group:t1");
    const revealed = revealStep(tree, new Set(), "t3");
    expect(ids(visibleCallRows(tree, revealed))).toEqual([
      "w1",
      "c1",
      "group:t1",
      "t1",
      "t2",
      "t3",
      "t4",
      "c2",
    ]);
    expect(rowForStep(tree, revealed, "t3")).toBe("t3");
  });

  it("expands everything on request and maps rows back to steps", () => {
    expect(ids(visibleCallRows(tree, expandAll(tree)))).toEqual([
      "w1",
      "layer:w1",
      "h1",
      "layer:w2",
      "h2",
      "layer:w3",
      "c1",
      "group:t1",
      "t1",
      "t2",
      "t3",
      "t4",
      "c2",
    ]);
    expect(firstStepOfRow(tree, "group:t1")).toBe("t1");
    expect(callPath(tree, "h2")).toEqual(["w1", "h2"]);
  });
});

describe("recorded traces", () => {
  it("opens the 879-step recording small and keeps every step reachable", async () => {
    const big = indexTrace(await loadFixture("recorded-sale-order-action-confirm"));
    const bigTree = buildCallTree(big);
    const covered = new Set(bigTree.nodeOfStep.keys());
    expect(covered.size).toBe(879);
    const initial = visibleCallRows(bigTree, new Set());
    const all = visibleCallRows(bigTree, expandAll(bigTree));
    // action_confirm changes 156 values in many places; everything else starts folded
    expect(initial.length).toBeLessThan(big.ordered.length / 5);
    expect(all.length).toBe(bigTree.nodes.size + bigTree.groups.size + bigTree.layers.size);
  });
});
