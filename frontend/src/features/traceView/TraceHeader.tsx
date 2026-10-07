import { ChevronRight, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import type { Trace } from "@/datasource";
import { formatDateTime, formatSpan } from "@/lib/format";
import { Button, Icon, Toolbar, ToolbarSpacer } from "@/ui";

import { TraceStatusBadge } from "../traces/TraceBadges";
import styles from "./TraceView.module.css";

export interface TraceHeaderProps {
  trace: Trace;
  onRunAgain: () => void;
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.headerFact}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

/** Where you are and what you can do (first row); what the run was (second row, data only). */
export function TraceHeader({ trace, onRunAgain }: TraceHeaderProps) {
  const records = trace.payload?.entrypoint.record_ids ?? [];
  return (
    <>
      <Toolbar>
        <nav aria-label="Breadcrumb" className={styles.breadcrumb}>
          <Link to="/traces" className={styles.crumb}>
            Traces
          </Link>
          <Icon icon={ChevronRight} compact />
          <h1 className={styles.title}>
            {trace.entrypoint_model}.{trace.entrypoint_method}
          </h1>
        </nav>
        <ToolbarSpacer />
        <Button compact icon={RotateCcw} onClick={onRunAgain}>
          Run again
        </Button>
      </Toolbar>
      <dl className={styles.summary}>
        <Fact label="Status">
          <TraceStatusBadge status={trace.status} />
        </Fact>
        <Fact label="Mode">{trace.dry_run ? "Dry run" : "Committed"}</Fact>
        <Fact label="Records">
          <code>{records.length > 0 ? records.join(", ") : "model"}</code>
        </Fact>
        <Fact label="Started">
          <time dateTime={trace.started_at}>{formatDateTime(trace.started_at)}</time>
        </Fact>
        <Fact label="Duration">{formatSpan(trace.started_at, trace.finished_at)}</Fact>
        {trace.odoo_version ? <Fact label="Odoo">{trace.odoo_version}</Fact> : null}
      </dl>
      {trace.dry_run ? null : (
        <div className={styles.dangerBanner} role="alert">
          <strong>Not a dry run.</strong> This run was committed in the Odoo database; its changes
          are real.
        </div>
      )}
    </>
  );
}
