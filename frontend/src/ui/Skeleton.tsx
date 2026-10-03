import styles from "./Skeleton.module.css";

export interface SkeletonProps {
  /** Number of placeholder rows. */
  rows?: number;
  /** Accessible text announced while loading, e.g. "Loading traces". */
  label: string;
}

/** Static placeholder rows (no shimmer) in the shape of a list while data loads. */
export function Skeleton({ rows = 3, label }: SkeletonProps) {
  return (
    <div className={styles.skeleton} role="status" aria-live="polite" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={styles.row} aria-hidden="true" />
      ))}
    </div>
  );
}
