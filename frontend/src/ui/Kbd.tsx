import type { ReactNode } from "react";

import styles from "./Kbd.module.css";

/** A key or key combination, e.g. <Kbd>?</Kbd> or <Kbd>Space</Kbd>. */
export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className={styles.kbd}>{children}</kbd>;
}
