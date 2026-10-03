import { Link, useLocation } from "react-router";

import { buttonClassName, EmptyState } from "@/ui";

import styles from "./Page.module.css";

export function NotFoundPage() {
  const { pathname } = useLocation();
  return (
    <main className={styles.page}>
      <div className={styles.section}>
        <EmptyState
          message={`There is no page at ${pathname}.`}
          action={
            <Link to="/traces" className={buttonClassName("primary")}>
              Go to traces
            </Link>
          }
        />
      </div>
    </main>
  );
}
