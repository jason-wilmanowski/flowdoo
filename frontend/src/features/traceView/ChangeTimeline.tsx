import { useMemo } from "react";

import type { TraceIndex } from "@/lib/replay/traceIndex";
import { DiffRow } from "@/ui";

import { changesOverTime } from "./model/changes";
import { formatValue } from "./model/values";
import styles from "./TraceView.module.css";

const STATE_CLASSES = {
  earlier: styles.timelineEarlier,
  current: styles.timelineCurrent,
  later: styles.timelineLater,
};

export interface ChangeTimelineProps {
  index: TraceIndex;
  /** Replay position: later changes have not happened yet and are dimmed. */
  position: number | null;
  onSelect: (stepId: string) => void;
}

/** Every field change of the run in order, relative to the replay position. */
export function ChangeTimeline({ index, position, onSelect }: ChangeTimelineProps) {
  const changes = useMemo(() => changesOverTime(index), [index]);
  if (changes.length === 0) {
    return <p className={styles.hint}>This run changed no field values.</p>;
  }
  const done = changes.filter((item) => position !== null && item.position <= position).length;
  return (
    <div className={styles.timeline}>
      <p className={styles.hint}>
        {done} of {changes.length} changes happened up to the current step. Select one to jump to
        its step.
      </p>
      <ol className={styles.timelineList}>
        {changes.map((item, i) => {
          const state =
            position === null || item.position > position
              ? "later"
              : item.position === position
                ? "current"
                : "earlier";
          return (
            <li key={`${item.step.id}-${String(i)}`} className={STATE_CLASSES[state]}>
              <button
                type="button"
                className={styles.timelineStep}
                aria-current={state === "current" ? "step" : undefined}
                onClick={() => {
                  onSelect(item.step.id);
                }}
              >
                <span className={styles.timelinePosition}>#{item.position + 1}</span>
                <code>
                  {item.change.model} {item.change.record_id}
                </code>
                {state === "later" ? <span className={styles.muted}>(not yet)</span> : null}
              </button>
              <DiffRow
                field={item.change.field}
                oldValue={formatValue(item.change.old)}
                newValue={formatValue(item.change.new)}
              />
            </li>
          );
        })}
      </ol>
    </div>
  );
}
