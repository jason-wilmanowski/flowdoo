import { CodeValue } from "./CodeValue";
import styles from "./DiffRow.module.css";

export interface DiffRowProps {
  field: string;
  /** Values already formatted for display. */
  oldValue: string;
  newValue: string;
}

/** `field  − old → + new`; the symbols carry the meaning as well as the colors. */
export function DiffRow({ field, oldValue, newValue }: DiffRowProps) {
  return (
    <div className={styles.diffRow}>
      <code className={styles.field}>{field}</code>
      <span className={styles.values}>
        <span className={styles.side}>
          <span className={styles.symbol} aria-hidden="true">
            −
          </span>
          <span className={styles.visuallyHidden}>old value</span>
          <CodeValue value={oldValue} label={`old ${field}`} tone="old" />
        </span>
        <span className={styles.arrow} aria-hidden="true">
          →
        </span>
        <span className={styles.side}>
          <span className={styles.symbol} aria-hidden="true">
            +
          </span>
          <span className={styles.visuallyHidden}>new value</span>
          <CodeValue value={newValue} label={`new ${field}`} tone="new" />
        </span>
      </span>
    </div>
  );
}
