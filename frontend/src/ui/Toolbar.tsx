import type { ComponentProps } from "react";

import styles from "./Toolbar.module.css";

/** A row of controls above a view (filters, actions). Use `end` for right-aligned items. */
export function Toolbar({ className, ...rest }: ComponentProps<"div">) {
  return <div className={[styles.toolbar, className ?? ""].join(" ").trim()} {...rest} />;
}

/** Pushes the following items to the right end of the toolbar. */
export function ToolbarSpacer() {
  return <span className={styles.spacer} aria-hidden="true" />;
}
