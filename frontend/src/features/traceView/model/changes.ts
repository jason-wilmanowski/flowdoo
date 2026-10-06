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

/** Net effect on one field within a call: first old value, last new value. */
export interface FieldEffect {
  field: string;
  old: FieldChange["old"];
  new: FieldChange["new"];
  /** How many steps wrote this field. */
  writes: number;
  /** The step that wrote the final value (to jump to it). */
  lastStepId: string;
  lastPosition: number;
}

export interface RecordEffect {
  model: string;
  recordId: number;
  /** The record was created within the call. */
  created: boolean;
  fields: FieldEffect[];
}

/** Steps of the call: the step and everything it called, in replay order. */
export function subtreeSteps(index: TraceIndex, stepId: string): Step[] {
  const result: Step[] = [];
  const stack = [stepId];
  for (let id = stack.pop(); id !== undefined; id = stack.pop()) {
    const step = index.byId.get(id);
    if (step) result.push(step);
    for (const child of index.childrenById.get(id) ?? []) stack.push(child);
  }
  return result.sort((a, b) => a.seq - b.seq);
}

/**
 * What a call changed, including everything it called: per record and field the value
 * before and after, the number of writes and the step that wrote last.
 */
export function netChanges(index: TraceIndex, stepId: string): RecordEffect[] {
  const records = new Map<string, RecordEffect & { byField: Map<string, FieldEffect> }>();
  for (const step of subtreeSteps(index, stepId)) {
    const position = index.positionById.get(step.id) ?? 0;
    for (const change of step.changes) {
      const key = `${change.model}#${String(change.record_id)}`;
      let record = records.get(key);
      if (!record) {
        record = {
          model: change.model,
          recordId: change.record_id,
          created: false,
          fields: [],
          byField: new Map(),
        };
        records.set(key, record);
      }
      if (step.kind === "orm_create") record.created = true;
      const effect = record.byField.get(change.field);
      if (effect) {
        effect.new = change.new;
        effect.writes += 1;
        effect.lastStepId = step.id;
        effect.lastPosition = position;
      } else {
        const created: FieldEffect = {
          field: change.field,
          old: change.old,
          new: change.new,
          writes: 1,
          lastStepId: step.id,
          lastPosition: position,
        };
        record.byField.set(change.field, created);
        record.fields.push(created);
      }
    }
  }
  return [...records.values()].map(({ byField: _unused, ...record }) => record);
}
