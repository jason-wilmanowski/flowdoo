import type { ReactNode } from "react";

import styles from "./EmptyState.module.css";

export interface EmptyStateProps {
  /** One sentence: what is missing and what to do next. */
  message: string;
  /** At most one action, usually a primary Button. */
  action?: ReactNode;
  /** "danger" for error states: the message says what went wrong. */
  tone?: "neutral" | "danger";
}

export function EmptyState({ message, action, tone = "neutral" }: EmptyStateProps) {
  return (
    <div className={styles.emptyState} role={tone === "danger" ? "alert" : undefined}>
      <p className={tone === "danger" ? styles.danger : styles.message}>{message}</p>
      {action}
    </div>
  );
}
