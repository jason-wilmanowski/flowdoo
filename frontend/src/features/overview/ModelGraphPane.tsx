import type { Edge, NodeMouseHandler } from "@xyflow/react";
import { useMemo } from "react";

import type { ModelSummary } from "@/api/types";
import { Checkbox, EmptyState } from "@/ui";
import { GraphCanvas } from "@/ui/GraphCanvas";
import type { GraphNodeType } from "@/ui/GraphNode";

import { neighborhood, type NeighborOptions } from "./model/neighborhood";
import styles from "./Overview.module.css";

export interface ModelGraphPaneProps {
  models: readonly ModelSummary[];
  selected: string | null;
  options: NeighborOptions;
  /** A model to point out (e.g. the target of the field under the mouse in the details). */
  highlight: string | null;
  onOptions: (options: NeighborOptions) => void;
  onSelect: (model: string) => void;
}

/** The selected model and its neighbours: what it links to, what links to it, its parents. */
export function ModelGraphPane({
  models,
  selected,
  options,
  highlight,
  onOptions,
  onSelect,
}: ModelGraphPaneProps) {
  const graph = useMemo(
    () => (selected === null ? null : neighborhood(models, selected, options)),
    [models, selected, options],
  );

  const nodes = useMemo<GraphNodeType[]>(
    () =>
      graph?.nodes.map((node) => ({
        id: node.id,
        type: "flowdoo",
        position: { x: node.x, y: node.y },
        data: {
          model: node.model,
          module: node.role === "more" ? null : node.module,
          detail: node.detail,
          active: node.role === "center",
          highlighted: node.role !== "more" && node.model === highlight,
          ...(node.role === "parent" ? { variant: "inherited" as const } : {}),
        },
      })) ?? [],
    [graph, highlight],
  );
  const highlightedIds = useMemo(
    () => new Set(nodes.filter((node) => node.data.highlighted).map((node) => node.id)),
    [nodes],
  );
  const edges = useMemo<Edge[]>(
    () =>
      // no labels on the lines (they covered each other); the fields are in the details
      graph?.edges.map((edge) => {
        const marked = highlightedIds.has(edge.source) || highlightedIds.has(edge.target);
        const inherits = edge.kind === "inherits";
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          // inheritance comes from above (dashed), relations from the sides (solid)
          ...(inherits ? { sourceHandle: "bottom", targetHandle: "top" } : {}),
          style: {
            ...(inherits ? { strokeDasharray: "5 4", stroke: "var(--text-subtle)" } : {}),
            ...(marked ? { stroke: "var(--accent)", strokeWidth: 2 } : {}),
          },
          zIndex: marked ? 1 : 0,
        };
      }) ?? [],
    [graph, highlightedIds],
  );

  const onNodeClick: NodeMouseHandler<GraphNodeType> = (_, node) => {
    if (!node.id.startsWith("more:") && !node.id.startsWith("center:")) onSelect(node.data.model);
  };

  return (
    <div className={styles.graphPane}>
      <div className={styles.graphToolbar} role="group" aria-label="Relations shown">
        <Checkbox
          label="Links to"
          checked={options.outgoing}
          onChange={(event) => {
            onOptions({ ...options, outgoing: event.target.checked });
          }}
        />
        <Checkbox
          label="Linked from"
          checked={options.incoming}
          onChange={(event) => {
            onOptions({ ...options, incoming: event.target.checked });
          }}
        />
        <Checkbox
          label="Inherits"
          checked={options.parents}
          onChange={(event) => {
            onOptions({ ...options, parents: event.target.checked });
          }}
        />
        <span className={styles.toolbarSpacer} />
        <span className={styles.legend}>Click a model to open it</span>
      </div>
      {selected === null ? (
        <EmptyState message="Select a model on the left to see what it links to and what links to it." />
      ) : (
        <div className={styles.canvas}>
          {/* a new model starts a new canvas, so it is fitted into view */}
          <GraphCanvas
            key={selected}
            label={`Relations of ${selected}`}
            nodes={nodes}
            edges={edges}
            onNodeClick={onNodeClick}
          />
        </div>
      )}
    </div>
  );
}
