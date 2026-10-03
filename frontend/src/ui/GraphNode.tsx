import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

import { Badge } from "./Badge";
import styles from "./GraphNode.module.css";

export interface GraphNodeData extends Record<string, unknown> {
  /** Technical model name, shown exactly as in Odoo, e.g. "sale.order". */
  model: string;
  /** Module of the implementation, or null for Odoo core. */
  module: string | null;
  /** Optional second line, e.g. the method name. */
  detail?: string;
  /** The step under the replay cursor. */
  active?: boolean;
}

export type GraphNodeType = Node<GraphNodeData, "flowdoo">;

/** A node in a graph: model name in mono, module badge, optional detail line. */
export function GraphNode({ data }: NodeProps<GraphNodeType>) {
  return (
    <div className={[styles.node, data.active ? styles.active : ""].join(" ").trim()}>
      <Handle type="target" position={Position.Left} className={styles.handle} />
      <div className={styles.header}>
        <span className={styles.model}>{data.model}</span>
        <Badge mono>{data.module ?? "core"}</Badge>
      </div>
      {data.detail ? <div className={styles.detail}>{data.detail}</div> : null}
      {data.active ? <span className={styles.visuallyHidden}>(current step)</span> : null}
      <Handle type="source" position={Position.Right} className={styles.handle} />
    </div>
  );
}
