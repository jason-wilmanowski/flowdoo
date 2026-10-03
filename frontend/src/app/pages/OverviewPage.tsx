import { Link } from "react-router";

import { buttonClassName, EmptyState } from "@/ui";

import styles from "./Page.module.css";

export function OverviewPage() {
  return (
    <main className={styles.page}>
      <div className={styles.section}>
        <h1 className={styles.heading}>Overview</h1>
        <EmptyState
          message="The overview of models, fields and relations is not available yet. It comes with milestone M6."
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
