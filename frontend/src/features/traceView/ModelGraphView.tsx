import type { Edge, NodeMouseHandler } from "@xyflow/react";
import { useMemo } from "react";

import type { TraceIndex } from "@/lib/replay/traceIndex";
import { GraphCanvas } from "@/ui/GraphCanvas";
import type { GraphNodeType } from "@/ui/GraphNode";

import { layoutLayers, modelGraph } from "./model/modelGraph";

const SPACING = { column: 320, row: 96 };

export interface ModelGraphViewProps {
  index: TraceIndex;
  /** Model of the step at the replay position. */
  activeModel: string | null;
  /** Click on a model: jump to its first step. */
  onModel: (model: string) => void;
}

/** Models of the run and who calls whom; the model of the current step is marked. */
export function ModelGraphView({ index, activeModel, onModel }: ModelGraphViewProps) {
  const graph = useMemo(() => modelGraph(index), [index]);
  const positions = useMemo(() => layoutLayers(graph.nodes, SPACING), [graph]);

  const nodes = useMemo<GraphNodeType[]>(
    () =>
      graph.nodes.map((node) => ({
        id: node.model,
        type: "flowdoo",
        position: positions.get(node.model) ?? { x: 0, y: 0 },
        data: {
          model: node.model,
          module: node.modules[0] ?? null,
          detail: [
            `${String(node.calls)} steps`,
            node.changes > 0 ? `${String(node.changes)} changes` : null,
            node.modules.length > 1 ? `${String(node.modules.length)} modules` : null,
          ]
            .filter(Boolean)
            .join(", "),
          active: node.model === activeModel,
        },
      })),
    [graph, positions, activeModel],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => ({
        id: `${edge.source}→${edge.target}`,
        source: edge.source,
        target: edge.target,
        label: edge.calls > 1 ? String(edge.calls) : undefined,
      })),
    [graph],
  );

  const onNodeClick: NodeMouseHandler<GraphNodeType> = (_, node) => {
    onModel(node.id);
  };

  return (
    <GraphCanvas
      label={`Models of the run: ${String(graph.nodes.length)} models`}
      nodes={nodes}
      edges={edges}
      onNodeClick={onNodeClick}
    />
  );
}
