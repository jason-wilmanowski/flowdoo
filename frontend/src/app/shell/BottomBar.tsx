import type { ReactNode } from "react";

import styles from "./BottomBar.module.css";

/** Optional bar below the panels (replay controls later). */
export function BottomBar({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className={styles.bottomBar} aria-label={label}>
      {children}
    </section>
  );
}
