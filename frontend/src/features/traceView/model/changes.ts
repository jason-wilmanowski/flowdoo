import type { FieldChange, Step } from "@/generated/trace";
import type { TraceIndex } from "@/lib/replay/traceIndex";

export interface TimedChange {
  step: Step;
  position: number;
  change: FieldChange;
}

/** Every field change of the run in replay order. */
export function changesOverTime(index: TraceIndex): TimedChange[] {
  const result: TimedChange[] = [];
  index.ordered.forEach((step, position) => {
    for (const change of step.changes) result.push({ step, position, change });
  });
  return result;
}

/** Changes of one step grouped by record, e.g. "sale.order 1" -> [state, date_order]. */
export function changesByRecord(
  step: Step,
): { model: string; recordId: number; changes: FieldChange[] }[] {
  const groups = new Map<string, { model: string; recordId: number; changes: FieldChange[] }>();
  for (const change of step.changes) {
    const key = `${change.model}#${String(change.record_id)}`;
    let group = groups.get(key);
    if (!group) {
      group = { model: change.model, recordId: change.record_id, changes: [] };
      groups.set(key, group);
    }
    group.changes.push(change);
  }
  return [...groups.values()];
}
