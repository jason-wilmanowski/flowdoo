import { useState } from "react";
import { Link } from "react-router";

import type { TraceSummary } from "@/api/types";
import { formatDateTime, formatSpan } from "@/lib/format";
import { Button, buttonClassName, CodeValue, Dialog } from "@/ui";

import { DryRunBadge, TraceStatusBadge } from "../traces/TraceBadges";
import styles from "./TraceList.module.css";

export interface TraceDetailsProps {
  trace: TraceSummary | null;
  /** Message of a failed delete, shown next to the action. */
  deleteError: string | null;
  onDelete: (id: string) => Promise<void>;
}

/** Summary of the selected trace with the actions on it. */
export function TraceDetails({ trace, deleteError, onDelete }: TraceDetailsProps) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (!trace) {
    return <p className={styles.hint}>Select a trace to see its details.</p>;
  }

  const rows: [string, React.ReactNode][] = [
    ["Status", <TraceStatusBadge key="s" status={trace.status} />],
    ["Run", <DryRunBadge key="r" dryRun={trace.dry_run} />],
    ["Started", <span className={styles.mono}>{formatDateTime(trace.started_at)}</span>],
    ["Finished", <span className={styles.mono}>{formatDateTime(trace.finished_at)}</span>],
    [
      "Duration",
      <span className={styles.mono}>{formatSpan(trace.started_at, trace.finished_at)}</span>,
    ],
    ["Odoo", <span className={styles.mono}>{trace.odoo_version ?? "—"}</span>],
    ["Schema", <span className={styles.mono}>{trace.schema_version ?? "—"}</span>],
    ["Trace ID", <CodeValue value={trace.id} label="trace ID" />],
  ];

  return (
    <div className={styles.details}>
      <h2 className={styles.detailsTitle}>
        {trace.entrypoint_model}.{trace.entrypoint_method}
      </h2>
      <dl className={styles.facts}>
        {rows.map(([term, value]) => (
          <div key={term} className={styles.fact}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {trace.error ? (
        <p className={styles.error} role="alert">
          <strong>Recording failed:</strong> {trace.error}
        </p>
      ) : null}
      <div className={styles.actions}>
        <Link to={`/traces/${trace.id}`} className={buttonClassName("primary", true)}>
          Open trace
        </Link>
        <Button
          compact
          onClick={() => {
            setConfirming(true);
          }}
        >
          Delete…
        </Button>
      </div>
      {deleteError ? (
        <p className={styles.error} role="alert">
          {deleteError}
        </p>
      ) : null}

      <Dialog open={confirming} onOpenChange={setConfirming} title="Delete trace?">
        <p className={styles.dialogText}>
          <span className={styles.mono}>
            {trace.entrypoint_model}.{trace.entrypoint_method}
          </span>{" "}
          from {formatDateTime(trace.started_at)} is removed from Flowdoo. Your Odoo database is not
          affected.
        </p>
        <div className={styles.dialogActions}>
          <Button
            variant="ghost"
            onClick={() => {
              setConfirming(false);
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            loading={deleting}
            onClick={() => {
              setDeleting(true);
              void onDelete(trace.id).finally(() => {
                setDeleting(false);
                setConfirming(false);
              });
            }}
          >
            Delete trace
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
