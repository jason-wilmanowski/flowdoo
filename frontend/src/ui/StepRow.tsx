import type { LucideIcon } from "lucide-react";

import { Badge } from "./Badge";
import { Icon } from "./Icon";
import styles from "./StepRow.module.css";

export interface StepRowProps {
  kindIcon: LucideIcon;
  /** Text for the kind, e.g. "write"; read by screen readers and shown as tooltip. */
  kindLabel: string;
  model: string;
  method: string;
  /** Module of the implementation; null = Odoo core. */
  module: string | null;
  duration: string;
  /** Number of field changes in this step, shown as a marker when > 0. */
  changes?: number;
  failed?: boolean;
}

/** `[kind] model.method  [module]  duration` in one dense row. */
export function StepRow({
  kindIcon,
  kindLabel,
  model,
  method,
  module,
  duration,
  changes = 0,
  failed = false,
}: StepRowProps) {
  return (
    <span className={styles.stepRow}>
      <span className={styles.kind} title={kindLabel}>
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
      {failed ? <Badge tone="danger">error</Badge> : null}
      <Badge mono>{module ?? "core"}</Badge>
      <span className={styles.duration}>{duration}</span>
    </span>
  );
}
