import { render, screen } from "@testing-library/react";

import { GraphCanvas } from "./GraphCanvas";
import type { GraphNodeType } from "./GraphNode";

const NODES: GraphNodeType[] = [
  {
    id: "a",
    type: "flowdoo",
    position: { x: 0, y: 0 },
    data: { model: "sale.order", module: "sale", detail: "action_confirm" },
  },
  {
    id: "b",
    type: "flowdoo",
    position: { x: 300, y: 0 },
    data: { model: "stock.picking", module: null, active: true },
  },
];

describe("GraphCanvas", () => {
  it("renders a labelled region with our nodes", () => {
    render(
      <div style={{ width: 800, height: 400 }}>
        <GraphCanvas
          label="Call graph"
          nodes={NODES}
          edges={[{ id: "e", source: "a", target: "b" }]}
        />
      </div>,
    );
    expect(screen.getByRole("region", { name: "Call graph" })).toBeInTheDocument();
    expect(screen.getByText("sale.order")).toBeInTheDocument();
    expect(screen.getByText("action_confirm")).toBeInTheDocument();
    expect(screen.getByText("core")).toBeInTheDocument();
    expect(screen.getByText("(current step)")).toBeInTheDocument();
  });
});
