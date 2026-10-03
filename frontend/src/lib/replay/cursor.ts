import type { Step } from "@/generated/trace";
import { pathTo, type TraceIndex } from "@/lib/replay/traceIndex";

/**
 * Replay cursor: a position in seq order (0 … stepCount − 1), or null for a trace without
 * steps. Every move is clamped to the bounds; nothing wraps around.
 */
export type Cursor = number | null;

export function clampCursor(position: number, stepCount: number): Cursor {
  if (stepCount <= 0) return null;
  return Math.min(Math.max(Math.trunc(position), 0), stepCount - 1);
}

export const firstStep = (stepCount: number): Cursor => clampCursor(0, stepCount);
export const lastStep = (stepCount: number): Cursor => clampCursor(stepCount - 1, stepCount);
export const nextStep = (cursor: Cursor, stepCount: number): Cursor =>
  clampCursor(cursor === null ? 0 : cursor + 1, stepCount);
export const previousStep = (cursor: Cursor, stepCount: number): Cursor =>
  clampCursor(cursor === null ? 0 : cursor - 1, stepCount);

export const isAtEnd = (cursor: Cursor, stepCount: number): boolean =>
  cursor === null || cursor >= stepCount - 1;

export function stepAt(index: TraceIndex, cursor: Cursor): Step | null {
  return cursor === null ? null : (index.ordered[cursor] ?? null);
}

/** Ids from the top-level step to the step under the cursor: the "active path". */
export function activePath(index: TraceIndex, cursor: Cursor): string[] {
  const step = stepAt(index, cursor);
  return step ? pathTo(index, step.id) : [];
}

export function cursorOf(index: TraceIndex, stepId: string): Cursor {
  return index.positionById.get(stepId) ?? null;
}
