// avoid-ai-design-ignore: I3 (Lucide is the only icon set; Check marks an applied change)
import { Check } from "lucide-react";
import { useMemo } from "react";

import type { TraceIndex } from "@/lib/replay/traceIndex";
import { Icon } from "@/ui";

import { changesOverTime } from "./model/changes";
import { formatValue } from "./model/values";
import styles from "./ChangeTimeline.module.css";

type State = "done" | "current" | "upcoming";

const STATE_LABELS: Record<State, string> = {
  done: "applied",
  current: "applied in the current step",
  upcoming: "not applied yet",
};

const MARKER_CLASSES: Record<State, string | undefined> = {
  done: styles.markerDone,
  current: styles.markerCurrent,
  upcoming: styles.markerUpcoming,
};

export interface ChangeTimelineProps {
  index: TraceIndex;
  /** Replay position: changes after it have not happened yet. */
  position: number | null;
  onSelect: (stepId: string) => void;
}

/**
 * Every field change of the run in order: a dense, high-contrast overview. The replay
 * position splits it into applied and upcoming changes (marked, not dimmed).
 */
export function ChangeTimeline({ index, position, onSelect }: ChangeTimelineProps) {
  const changes = useMemo(() => changesOverTime(index), [index]);
  if (changes.length === 0) {
    return <p className={styles.empty}>This run changed no field values.</p>;
  }
  const applied = changes.filter((item) => position !== null && item.position <= position).length;

  return (
    <div className={styles.timeline}>
      <p className={styles.summary}>
        <strong>{applied}</strong> of <strong>{changes.length}</strong> changes applied up to step{" "}
        {position === null ? 0 : position + 1}. Select a change to jump to the step that made it.
      </p>
      <ol className={styles.list}>
        {changes.map((item, i) => {
          const state: State =
            position === null || item.position > position
              ? "upcoming"
              : item.position === position
                ? "current"
                : "done";
          const oldValue = formatValue(item.change.old);
          const newValue = formatValue(item.change.new);
          const record = `${item.change.model} ${String(item.change.record_id)}`;
          return (
            <li key={`${item.step.id}-${String(i)}`}>
              <button
                type="button"
                className={[styles.row, state === "current" ? styles.current : ""].join(" ").trim()}
                aria-current={state === "current" ? "step" : undefined}
                aria-label={`Step ${String(item.position + 1)}: ${record} ${item.change.field} ${oldValue} to ${newValue}, ${STATE_LABELS[state]}`}
                onClick={() => {
                  onSelect(item.step.id);
                }}
              >
                <span
                  className={[styles.marker, MARKER_CLASSES[state]].join(" ")}
                  aria-hidden="true"
                >
                  {state === "done" ? <Icon icon={Check} compact /> : null}
                </span>
                <span className={styles.step}>{item.position + 1}</span>
                <span className={styles.record} title={record}>
                  {item.change.model}{" "}
                  <span className={styles.recordId}>#{item.change.record_id}</span>
                </span>
                <span className={styles.field} title={item.change.field}>
                  {item.change.field}
                </span>
                <span className={styles.old} title={oldValue}>
                  {oldValue}
                </span>
                <span className={styles.arrow} aria-hidden="true">
                  →
                </span>
                <span className={styles.new} title={newValue}>
                  {newValue}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
