import type { TraceSummary } from "@/api/types";
import { Badge, type BadgeTone } from "@/ui";

const STATUS_TONES: Record<TraceSummary["status"], BadgeTone> = {
  pending: "neutral",
  running: "accent",
  succeeded: "success",
  failed: "danger",
};

/** Recording status in words; the tone only supports the text. */
export function TraceStatusBadge({ status }: { status: TraceSummary["status"] }) {
  return <Badge tone={STATUS_TONES[status]}>{status}</Badge>;
}

/** Whether the run was rolled back; a run that was not is marked as dangerous. */
export function DryRunBadge({ dryRun }: { dryRun: boolean }) {
  return dryRun ? <Badge>dry run</Badge> : <Badge tone="danger">not a dry run</Badge>;
}
