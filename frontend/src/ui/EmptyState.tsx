import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import styles from "./EmptyState.module.css";
import { Icon } from "./Icon";

export interface EmptyStateProps {
  /** One sentence: what is missing and what to do next. */
  message: string;
  /** At most one action, usually a primary Button. */
  action?: ReactNode;
  /** "danger" for error states: the message says what went wrong. */
  tone?: "neutral" | "danger";
  /** Fill the whole area and center the message, for a pane that has nothing to show yet. */
  fill?: boolean;
  /** Shown above the message (decorative). */
  icon?: LucideIcon;
}

export function EmptyState({
  message,
  action,
  tone = "neutral",
  fill = false,
  icon,
}: EmptyStateProps) {
  return (
    <div
      className={[styles.emptyState, fill ? styles.fill : ""].join(" ").trim()}
      role={tone === "danger" ? "alert" : undefined}
    >
      {icon ? <Icon icon={icon} className={styles.icon} /> : null}
      <p className={tone === "danger" ? styles.danger : styles.message}>{message}</p>
      {action}
    </div>
  );
}
