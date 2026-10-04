import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { formatDuration } from "@/lib/format";
import type { TraceIndex } from "@/lib/replay/traceIndex";
import { Button, StepRow, Tree } from "@/ui";

import { stepKind } from "../traces/stepKinds";
import { ancestorsOf, collapseBelow, revealStep, visibleRows } from "./model/treeRows";
import styles from "./TraceView.module.css";

/** Steps deeper than this start collapsed, so a big trace opens readable. */
const INITIAL_DEPTH = 2;

export interface StepTreePaneProps {
  index: TraceIndex;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Call tree of the run; the selected step is the replay position. */
export function StepTreePane({ index, selectedId, onSelect }: StepTreePaneProps) {
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(() =>
    collapseBelow(index, INITIAL_DEPTH),
  );

  // The replay can move into a collapsed part: the way to the selected step stays open.
  const effective = useMemo(
    () => (selectedId === null ? collapsed : revealStep(index, collapsed, selectedId)),
    [index, collapsed, selectedId],
  );
  const rows = useMemo(() => visibleRows(index, effective), [index, effective]);

  const selectedRef = useRef(selectedId);
  useEffect(() => {
    selectedRef.current = selectedId;
  });

  const onToggle = useCallback(
    (id: string, expanded: boolean) => {
      // Collapsing around the selected step moves the selection up, so it stays visible.
      const selected = selectedRef.current;
      if (!expanded && selected !== null && ancestorsOf(index, selected).includes(id)) onSelect(id);
      setCollapsed((current) => {
        const next = new Set(current);
        if (expanded) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    [index, onSelect],
  );

  const renderRow = useCallback(
    (id: string) => {
      const step = index.byId.get(id);
      if (!step) return null;
      const kind = stepKind(step.kind);
      return (
        <StepRow
          kindIcon={kind.icon}
          kindLabel={kind.label}
          model={step.model}
          method={step.method}
          module={step.module}
          duration={formatDuration(step.duration_ms)}
          changes={step.changes.length}
          failed={step.error !== null}
        />
      );
    },
    [index],
  );

  return (
    <div className={styles.pane}>
      <div className={styles.paneHeader}>
        <h2 className={styles.paneTitle}>Steps</h2>
        <span className={styles.count}>{index.ordered.length}</span>
        <span className={styles.spacer} />
        <Button
          variant="ghost"
          compact
          onClick={() => {
            setCollapsed(new Set());
          }}
        >
          Expand all
        </Button>
        <Button
          variant="ghost"
          compact
          onClick={() => {
            setCollapsed(collapseBelow(index, 1));
          }}
        >
          Collapse
        </Button>
      </div>
      <div className={styles.scroll}>
        <Tree
          label="Steps"
          rows={rows}
          renderRow={renderRow}
          selectedId={selectedId}
          onSelect={onSelect}
          onToggle={onToggle}
        />
      </div>
    </div>
  );
}
