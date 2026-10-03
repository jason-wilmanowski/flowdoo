import { Outlet } from "react-router";

import styles from "./AppShell.module.css";
import { ConnectionNotices } from "./ConnectionNotices";
import { TopBar } from "./TopBar";

/** Top bar and connection notices on every page; the page fills the rest (layout route). */
export function AppShell() {
  return (
    <div className={styles.shell}>
      <TopBar />
      <ConnectionNotices />
      <div className={styles.page}>
        <Outlet />
      </div>
    </div>
  );
}
