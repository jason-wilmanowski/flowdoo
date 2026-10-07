import type { LucideIcon } from "lucide-react";

import { Icon } from "./Icon";
import styles from "./StepRow.module.css";

export interface StepRowProps {
  kindIcon: LucideIcon;
  /** Text for the kind, e.g. "write"; read by screen readers and shown as tooltip. */
  kindLabel: string;
  /** Color of the kind icon: what the step did to data (the label says the same in words). */
  kindTone?: "neutral" | "add" | "change" | "remove";
  model: string;
  method: string;
  /** Module of the implementation; null = Odoo core. */
  module: string | null;
  /** Modules of a super chain, most derived first; shown instead of `module`. */
  chain?: readonly (string | null)[];
  /** Short context in front of the module, e.g. "in sale" for the layer that made the call. */
  note?: string;
  duration: string;
  /** Number of field changes in this step, shown as a marker when > 0. */
  changes?: number;
  failed?: boolean;
}

/** `[kind] model.method  [module]  duration` in one dense row. */
export function StepRow({
  kindIcon,
  kindLabel,
  kindTone = "neutral",
  model,
  method,
  module,
  chain,
  note,
  duration,
  changes = 0,
  failed = false,
}: StepRowProps) {
  const modules = chain && chain.length > 1 ? chain : [module];
  return (
    <span className={styles.stepRow}>
      <span className={[styles.kind, styles[kindTone]].join(" ")} title={kindLabel}>
        <Icon icon={kindIcon} compact label={kindLabel} />
      </span>
      <span className={[styles.name, failed ? styles.failed : ""].join(" ").trim()}>
        <span className={styles.model}>{model}</span>.{method}
      </span>
      {changes > 0 ? (
        <span className={styles.changes} title={`${String(changes)} field changes`}>
          Δ{changes}
          <span className={styles.visuallyHidden}> field changes</span>
        </span>
      ) : null}
      {failed ? <span className={styles.error}>error</span> : null}
      {note ? <span className={styles.note}>{note}</span> : null}
      <span
        className={styles.module}
        title={
          modules.length > 1
            ? `super() chain: ${modules.map((m) => m ?? "core").join(", ")}`
            : undefined
        }
      >
        {modules.map((m) => m ?? "core").join(" → ")}
      </span>
      <span className={styles.duration}>{duration}</span>
    </span>
  );
}
