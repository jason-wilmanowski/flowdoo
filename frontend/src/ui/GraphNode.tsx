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
  /** Pointed out from elsewhere, e.g. the field that links to this model. */
  highlighted?: boolean;
  /** "inherited": a model the centre inherits from (dashed, labelled), not a relation. */
  variant?: "inherited";
}

export type GraphNodeType = Node<GraphNodeData, "flowdoo">;

/** A node in a graph: model name in mono, module badge, optional detail line. */
export function GraphNode({ data }: NodeProps<GraphNodeType>) {
  return (
    <div
      className={[
        styles.node,
        data.active ? styles.active : "",
        data.highlighted ? styles.highlighted : "",
        data.variant === "inherited" ? styles.inherited : "",
      ]
        .join(" ")
        .trim()}
    >
      <Handle type="target" position={Position.Left} className={styles.handle} />
      <div className={styles.header}>
        <span className={styles.model}>{data.model}</span>
        {data.variant === "inherited" ? <span className={styles.kindTag}>inherited</span> : null}
        <Badge mono>{data.module ?? "core"}</Badge>
      </div>
      {data.detail ? <div className={styles.detail}>{data.detail}</div> : null}
      {data.active ? <span className={styles.visuallyHidden}>(current step)</span> : null}
      <Handle type="source" position={Position.Right} className={styles.handle} />
      {/* top and bottom: inheritance runs vertically, relations horizontally */}
      <Handle type="target" id="top" position={Position.Top} className={styles.handle} />
      <Handle type="source" id="bottom" position={Position.Bottom} className={styles.handle} />
    </div>
  );
}
