import type { ModelSummary } from "@/api/types";
import { loadRegistryFixture } from "@/datasource/fixtures/catalog";

import { neighborhood } from "./neighborhood";
import {
  DEFAULT_FILTER,
  filterModels,
  groupByModule,
  incomingRelations,
  modulesOf,
} from "./registry";

const model = (name: string, extra: Partial<ModelSummary> = {}): ModelSummary => ({
  model: name,
  description: null,
  module: "sale",
  modules: ["sale"],
  abstract: false,
  transient: false,
  parents: [],
  delegates: {},
  field_count: 3,
  relations: [],
  ...extra,
});

const MODELS = [
  model("sale.order", {
    description: "Sales Order",
    parents: ["mail.thread"],
    relations: [
      { field: "partner_id", type: "many2one", target: "res.partner" },
      { field: "partner_invoice_id", type: "many2one", target: "res.partner" },
      { field: "order_line", type: "one2many", target: "sale.order.line" },
      { field: "origin_order_id", type: "many2one", target: "sale.order" },
    ],
  }),
  model("sale.order.line", {
    relations: [{ field: "order_id", type: "many2one", target: "sale.order" }],
  }),
  model("res.partner", { module: "base", description: "Contact" }),
  model("mail.thread", { module: "mail", abstract: true }),
  model("sale.advance.payment.inv", { transient: true }),
  model("ir.model", { module: null }),
];

describe("model list", () => {
  it("filters by words, module, abstract and wizards", () => {
    const names = (filter = DEFAULT_FILTER) => filterModels(MODELS, filter).map((m) => m.model);
    expect(names()).not.toContain("sale.advance.payment.inv");
    expect(names({ ...DEFAULT_FILTER, query: "sales order" })).toEqual(["sale.order"]);
    expect(names({ ...DEFAULT_FILTER, query: "contact" })).toEqual(["res.partner"]);
    expect(names({ ...DEFAULT_FILTER, module: "core" })).toEqual(["ir.model"]);
    expect(names({ ...DEFAULT_FILTER, showAbstract: false })).not.toContain("mail.thread");
    expect(names({ ...DEFAULT_FILTER, showTransient: true })).toContain("sale.advance.payment.inv");
  });

  it("groups by defining module and lists the modules", () => {
    expect(groupByModule(MODELS).map(([module, list]) => [module, list.length])).toEqual([
      ["base", 1],
      ["core", 1],
      ["mail", 1],
      ["sale", 3],
    ]);
    expect(modulesOf(MODELS)).toEqual(["base", "core", "mail", "sale"]);
  });

  it("finds the fields that point to a model", () => {
    expect(incomingRelations(MODELS, "sale.order")).toEqual([
      { from: "sale.order.line", field: "order_id", type: "many2one" },
    ]);
  });
});

describe("neighborhood", () => {
  const options = { outgoing: true, incoming: true, parents: true, limit: 12 };

  it("puts targets right, sources left, parents above, one node per model", () => {
    const { nodes, edges } = neighborhood(MODELS, "sale.order", options);
    const at = (id: string) => nodes.find((n) => n.id === id)!;

    expect(at("center:sale.order")).toMatchObject({ x: 0, y: 0, detail: "Sales Order" });
    expect(at("target:res.partner")).toMatchObject({ detail: "via partner_id +1" });
    expect(edges.find((e) => e.target === "target:res.partner")?.label).toBe(
      "partner_id, partner_invoice_id",
    );
    expect(at("target:res.partner").x).toBeGreaterThan(0);
    expect(at("source:sale.order.line").x).toBeLessThan(0);
    // inherited models get a row of their own above every relation column
    const lowestColumnTop = Math.min(...nodes.filter((n) => n.role !== "parent").map((n) => n.y));
    expect(at("parent:mail.thread").y).toBeLessThan(lowestColumnTop);
    expect(edges.find((e) => e.source === "parent:mail.thread")?.kind).toBe("inherits");
    expect(edges.find((e) => e.target === "target:res.partner")?.kind).toBe("relation");
    // the self reference (origin_order_id) is not drawn
    expect(nodes.some((n) => n.model === "sale.order" && n.role !== "center")).toBe(false);
    expect(edges).toContainEqual({
      id: "source:sale.order.line->sale.order",
      source: "source:sale.order.line",
      target: "center:sale.order",
      label: "order_id",
      kind: "relation",
    });
  });

  it("summarises what does not fit", () => {
    const { nodes } = neighborhood(MODELS, "sale.order", { ...options, limit: 1 });
    expect(nodes.find((n) => n.id === "more:target")).toMatchObject({ model: "+ 1 more" });
  });

  it("handles a big real model", async () => {
    const { models } = await loadRegistryFixture();
    const { nodes } = neighborhood(models, "res.partner", { ...options, limit: 12 });
    expect(nodes.filter((n) => n.role === "source")).toHaveLength(12);
    expect(nodes.find((n) => n.id === "more:source")?.model).toMatch(/^\+ \d+ more$/);
  });
});
