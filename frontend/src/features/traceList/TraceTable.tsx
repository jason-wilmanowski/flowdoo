import type { TraceSummary } from "@/api/types";
import { formatDateTime, formatSpan, shortId } from "@/lib/format";
import { Table, type TableColumn } from "@/ui";

import { DryRunBadge, TraceStatusBadge } from "../traces/TraceBadges";
import styles from "./TraceList.module.css";

const COLUMNS: TableColumn<TraceSummary>[] = [
  {
    id: "status",
    header: "Status",
    shrink: true,
    cell: (trace) => <TraceStatusBadge status={trace.status} />,
  },
  {
    id: "entrypoint",
    header: "Entrypoint",
    cell: (trace) => (
      <span className={styles.mono}>
        {trace.entrypoint_model}.{trace.entrypoint_method}
      </span>
    ),
  },
  {
    id: "run",
    header: "Run",
    shrink: true,
    cell: (trace) => <DryRunBadge dryRun={trace.dry_run} />,
  },
  {
    id: "started",
    header: "Started",
    shrink: true,
    cell: (trace) => (
      <time className={styles.mono} dateTime={trace.started_at}>
        {formatDateTime(trace.started_at)}
      </time>
    ),
  },
  {
    id: "duration",
    header: "Duration",
    shrink: true,
    align: "end",
    cell: (trace) => (
      <span className={styles.mono}>{formatSpan(trace.started_at, trace.finished_at)}</span>
    ),
  },
  {
    id: "id",
    header: "ID",
    shrink: true,
    cell: (trace) => (
      <span className={styles.mono} title={trace.id}>
        {shortId(trace.id)}
      </span>
    ),
  },
];

export interface TraceTableProps {
  traces: readonly TraceSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onOpen: (id: string) => void;
}

export function TraceTable({ traces, selectedId, onSelect, onOpen }: TraceTableProps) {
  return (
    <Table
      label="Traces"
      columns={COLUMNS}
      rows={traces}
      rowId={(trace) => trace.id}
      selectedId={selectedId}
      onSelect={onSelect}
      onActivate={onOpen}
    />
  );
}
