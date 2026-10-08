import type { Step } from "@/generated/trace";
import { indexTrace } from "@/lib/replay/traceIndex";

import { buildCallTree } from "./callTree";
import { rowsContainingMatches, searchCalls } from "./search";

const step = (
  id: string,
  parent: string | null,
  seq: number,
  model: string,
  method: string,
  module: string | null,
  mro = 0,
): Step => ({
  id,
  parent_id: parent,
  seq,
  kind: "method_call",
  model,
  method,
  module,
  mro_position: mro,
  calls_super: true,
  record_ids: [],
  args_summary: null,
  return_summary: null,
  changes: [],
  duration_ms: 1,
  error: null,
});

const tree = buildCallTree(
  indexTrace({
    steps: [
      step("a", null, 1, "sale.order.line", "write", "sale_stock"),
      step("b", "a", 2, "sale.order.line", "write", "sale", 1),
      step("c", "b", 3, "account.tax", "_compute_taxes", "account"),
      step("d", "b", 4, "account.tax", "_round", "account"),
      step("e", null, 5, "sale.order", "_compute_amounts", "sale"),
    ],
  }),
);

describe("searchCalls", () => {
  it("finds calls by model, method or module, in call order", () => {
    expect(searchCalls(tree, "account.tax")).toEqual(["c", "d"]);
    expect(searchCalls(tree, "COMPUTE")).toEqual(["c", "e"]);
    // modules of every layer of a chain count
    expect(searchCalls(tree, "sale_stock")).toEqual(["a"]);
  });

  it("needs every word to match and ignores empty queries", () => {
    expect(searchCalls(tree, "line write")).toEqual(["a"]);
    expect(searchCalls(tree, "tax amounts")).toEqual([]);
    expect(searchCalls(tree, "   ")).toEqual([]);
  });

  it("knows which rows hold matches below them", () => {
    const rows = rowsContainingMatches(tree, searchCalls(tree, "account.tax"));
    // nothing changed values, so everything is folded: c and d into a group under the sale
    // layer of the write chain, the two top-level calls into a group of their own
    expect([...rows].sort()).toEqual(["a", "group:a", "group:c", "layer:b"]);
  });
});
