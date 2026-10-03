import "@xyflow/react/dist/base.css";

import { ReactFlow, type Edge, type NodeMouseHandler } from "@xyflow/react";

import styles from "./GraphCanvas.module.css";
import { GraphNode, type GraphNodeType } from "./GraphNode";

const NODE_TYPES = { flowdoo: GraphNode };
const EDGE_OPTIONS = { type: "step" } as const;

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
        fitView
      />
    </div>
  );
}
