import "@xyflow/react/dist/base.css";

import { ReactFlow, type Edge, type NodeMouseHandler } from "@xyflow/react";

import styles from "./GraphCanvas.module.css";
import { GraphNode, type GraphNodeType } from "./GraphNode";

const NODE_TYPES = { flowdoo: GraphNode };
// Label boxes on edges: we load only React Flow's base styles (our own theme), which do not
// colour them, and an SVG rect without a fill is drawn black.
const EDGE_OPTIONS = {
  type: "step",
  labelStyle: {
    fill: "var(--text-muted)",
    fontFamily: "var(--font-mono)",
    fontSize: "var(--text-xs)",
  },
  labelBgStyle: { fill: "var(--surface)", stroke: "var(--border)" },
  labelBgPadding: [6, 3] as [number, number],
  labelBgBorderRadius: 4,
} as const;
// The library's corner badge is hidden; React Flow is credited in the README.
const PRO_OPTIONS = { hideAttribution: true };

export interface GraphCanvasProps {
  /** Accessible name of the graph, e.g. "Call graph of sale.order.action_confirm". */
  label: string;
  /** Positioned nodes; layout happens outside (no layout algorithm here). */
  nodes: GraphNodeType[];
  edges: Edge[];
  onNodeClick?: NodeMouseHandler<GraphNodeType>;
}

/**
 * Read-only graph on React Flow with our node and edge styling: step-routed 1px edges,
 * no minimap, no background pattern, nodes not draggable or connectable.
 */
export function GraphCanvas({ label, nodes, edges, onNodeClick }: GraphCanvasProps) {
  return (
    <div className={styles.canvas} role="region" aria-label={label}>
      <ReactFlow<GraphNodeType>
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        defaultEdgeOptions={EDGE_OPTIONS}
        onNodeClick={onNodeClick}
        nodesDraggable={false}
        nodesConnectable={false}
        edgesFocusable={false}
        zoomOnDoubleClick={false}
        proOptions={PRO_OPTIONS}
        fitView
      />
    </div>
  );
}
