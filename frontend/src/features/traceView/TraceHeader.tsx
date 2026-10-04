import { ArrowLeft, RotateCcw } from "lucide-react";
import { Link } from "react-router";

import type { Trace } from "@/datasource";
import { formatDateTime, formatSpan } from "@/lib/format";
import { Button, Icon, Toolbar, ToolbarSpacer } from "@/ui";

import { DryRunBadge, TraceStatusBadge } from "../traces/TraceBadges";
import styles from "./TraceView.module.css";

export interface TraceHeaderProps {
  trace: Trace;
  onRunAgain: () => void;
}

/** What ran, on which records, when and how it ended. */
export function TraceHeader({ trace, onRunAgain }: TraceHeaderProps) {
  const records = trace.payload?.entrypoint.record_ids ?? [];
  return (
    <>
      <Toolbar>
        <Link to="/traces" className={styles.back}>
          <Icon icon={ArrowLeft} compact />
          Traces
        </Link>
        <h1 className={styles.title}>
          {trace.entrypoint_model}.{trace.entrypoint_method}
        </h1>
        {records.length > 0 ? (
          <span className={styles.meta}>
            on <code>{records.join(", ")}</code>
          </span>
        ) : null}
        <TraceStatusBadge status={trace.status} />
        <DryRunBadge dryRun={trace.dry_run} />
        <span className={styles.meta}>
          <time dateTime={trace.started_at}>{formatDateTime(trace.started_at)}</time>
        </span>
        <span className={styles.meta}>took {formatSpan(trace.started_at, trace.finished_at)}</span>
        {trace.odoo_version ? <span className={styles.meta}>Odoo {trace.odoo_version}</span> : null}
        <ToolbarSpacer />
        <Button compact icon={RotateCcw} onClick={onRunAgain}>
          Run again
        </Button>
      </Toolbar>
      {trace.dry_run ? null : (
        <div className={styles.dangerBanner} role="alert">
          <strong>Not a dry run.</strong> This run was committed in the Odoo database; its changes
          are real.
        </div>
      )}
    </>
  );
}
