import { LoaderCircle } from "lucide-react";

import { Icon } from "./Icon";
import styles from "./Spinner.module.css";

export interface SpinnerProps {
  /** Visible text next to the spinner, e.g. "Loading trace". */
  label?: string;
  compact?: boolean;
}

/** Loading indicator. Rotation stops under prefers-reduced-motion; the text stays. */
export function Spinner({ label, compact = false }: SpinnerProps) {
  return (
    <span className={styles.spinner} role="status" aria-live="polite">
      <Icon icon={LoaderCircle} compact={compact} className={styles.glyph} />
      {label ? <span>{label}</span> : <span className={styles.visuallyHidden}>Loading</span>}
    </span>
  );
}
