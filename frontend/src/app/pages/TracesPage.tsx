import { useEffect } from "react";
import { Link } from "react-router";
import { useStore } from "zustand";

import { Button, buttonClassName, EmptyState, Skeleton } from "@/ui";

import { useStores } from "../appContext";
import styles from "./Page.module.css";

/** Placeholder for the trace list: real loading, empty and error states, no list yet. */
export function TracesPage() {
  const { traceList } = useStores();
  const page = useStore(traceList, (state) => state.page);
  const phase = useStore(traceList, (state) => state.phase);
  const error = useStore(traceList, (state) => state.error);
  const load = useStore(traceList, (state) => state.load);

  useEffect(() => {
    void load();
  }, [load]);

  let content;
  if (phase === "error" && error) {
    content = (
      <EmptyState
        tone="danger"
        message={`Could not load the traces: ${error.message}`}
        action={
          <Button
            onClick={() => {
              void load();
            }}
          >
            Retry
          </Button>
        }
      />
    );
  } else if (phase !== "ready" || !page) {
    content = <Skeleton rows={6} label="Loading traces" />;
  } else if (page.total === 0) {
    content = (
      <EmptyState message="No traces recorded yet. Starting a trace from here comes with the start dialog; until then use POST /traces of the API." />
    );
  } else {
    const newest = page.items[0];
    content = (
      <EmptyState
        message={`${String(page.total)} traces recorded. The trace list is not built yet.`}
        action={
          newest ? (
            <Link to={`/traces/${newest.id}`} className={buttonClassName("primary")}>
              Open the newest trace
            </Link>
          ) : null
        }
      />
    );
  }

  return (
    <main className={styles.page}>
      <div className={styles.section}>
        <h1 className={styles.heading}>Traces</h1>
        {content}
      </div>
    </main>
  );
}
