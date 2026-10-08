import { Layers } from "lucide-react";
import { useCallback, useMemo } from "react";

import { formatDuration } from "@/lib/format";
import { Button, Icon, StepRow, Tree } from "@/ui";

import { stepKind } from "../traces/stepKinds";
import {
  expandAll,
  firstStepOfRow,
  rowForStep,
  visibleCallRows,
  type CallTree,
} from "./model/callTree";
import styles from "./TraceView.module.css";

export interface StepTreePaneProps {
  tree: CallTree;
  stepCount: number;
  /** Rows whose expansion differs from the default (relevant paths open). */
  toggled: ReadonlySet<string>;
  onToggled: (toggled: ReadonlySet<string>) => void;
  /** The step at the replay position. */
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
}

/**
 * The call tree: one row per call (super chains merged), only the paths to changes and
 * errors open at first, irrelevant runs folded. The row holding the replay position is
 * selected; replaying does not unfold the tree.
 */
export function StepTreePane({
  tree,
  stepCount,
  toggled,
  onToggled,
  selectedStepId,
  onSelectStep,
}: StepTreePaneProps) {
  const rows = useMemo(() => visibleCallRows(tree, toggled), [tree, toggled]);
  const selectedRow = selectedStepId === null ? null : rowForStep(tree, toggled, selectedStepId);

  const onToggle = useCallback(
    (id: string) => {
      const next = new Set(toggled);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      onToggled(next);
    },
    [toggled, onToggled],
  );

  const onSelect = useCallback(
    (rowId: string) => {
      const stepId = firstStepOfRow(tree, rowId);
      if (stepId !== null) onSelectStep(stepId);
    },
    [tree, onSelectStep],
  );

  const renderRow = useCallback(
    (id: string) => {
      const group = tree.groups.get(id);
      if (group) {
        return (
          <span className={styles.groupRow}>
            <Icon icon={Layers} compact />
            <span>
              {group.members.length} calls{" "}
              {group.model ? (
                <>
                  in <code>{group.model}</code>
                </>
              ) : (
                "without changes"
              )}
            </span>
            <span className={styles.groupSteps}>{group.stepCount} steps</span>
          </span>
        );
      }
      const layer = tree.layers.get(id);
      if (layer) {
        const { step } = layer;
        const last = tree.nodes.get(layer.nodeId)?.chain.at(-1)?.id === step.id;
        return (
          <span className={styles.layerRow}>
            <span className={styles.layerMro} title="Position in the MRO (0 = most derived)">
              {step.mro_position ?? "?"}
            </span>
            <code className={styles.layerModule}>{step.module ?? "core"}</code>
            <span
              className={
                step.calls_super === false && !last ? styles.layerSuperNo : styles.layerSuper
              }
            >
              {step.calls_super === null
                ? "super() not determined"
                : step.calls_super
                  ? "calls super()"
                  : "no super()"}
            </span>
            {step.changes.length > 0 ? (
              <span
                className={styles.layerChanges}
                title={`${String(step.changes.length)} field changes`}
              >
                Δ{step.changes.length}
              </span>
            ) : null}
            <span className={styles.groupSteps}>{formatDuration(step.duration_ms)}</span>
          </span>
        );
      }
      const node = tree.nodes.get(id);
      const head = node?.chain[0];
      if (!node || !head) return null;
      const kind = stepKind(head.kind);
      return (
        <StepRow
          kindIcon={kind.icon}
          kindLabel={kind.label}
          kindTone={kind.tone}
          model={head.model}
          method={head.method}
          module={head.module}
          chain={node.chain.map((layer) => layer.module)}
          duration={formatDuration(head.duration_ms)}
          changes={node.ownChanges}
          failed={node.failed}
        />
      );
    },
    [tree],
  );

  return (
    <div className={styles.pane}>
      <div className={styles.paneHeader}>
        <h2 className={styles.paneTitle}>Calls</h2>
        <span className={styles.count} title={`${String(stepCount)} recorded steps`}>
          {tree.nodes.size}
        </span>
        <span className={styles.spacer} />
        <Button
          variant="ghost"
          compact
          onClick={() => {
            onToggled(expandAll(tree));
          }}
        >
          Expand all
        </Button>
        <Button
          variant="ghost"
          compact
          disabled={toggled.size === 0}
          onClick={() => {
            onToggled(new Set());
          }}
        >
          Relevant only
        </Button>
      </div>
      <div className={styles.treeArea}>
        <Tree
          label="Calls"
          rows={rows}
          renderRow={renderRow}
          selectedId={selectedRow}
          onSelect={onSelect}
          onToggle={onToggle}
        />
      </div>
    </div>
  );
}
