import {
  Ban,
  Calculator,
  CircleCheck,
  OctagonX,
  Pencil,
  Plus,
  RefreshCcw,
  SquareFunction,
  Trash2,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import type { StepKind } from "@/generated/trace";

/** Fixed icon and label per step kind, the same everywhere in the UI. */
export const STEP_KINDS: Record<StepKind, { icon: LucideIcon; label: string }> = {
  method_call: { icon: SquareFunction, label: "method call" },
  orm_create: { icon: Plus, label: "create" },
  orm_write: { icon: Pencil, label: "write" },
  orm_unlink: { icon: Trash2, label: "unlink" },
  compute: { icon: Calculator, label: "compute" },
  onchange: { icon: RefreshCcw, label: "onchange" },
  constraint: { icon: CircleCheck, label: "constraint" },
  automation: { icon: Workflow, label: "automation" },
  side_effect_blocked: { icon: OctagonX, label: "blocked side effect" },
};

/** Fallback for kinds a newer recorder may add. */
export const UNKNOWN_KIND = { icon: Ban, label: "unknown" };

/** Icon and label of a kind, also for kinds this UI does not know yet. */
export function stepKind(kind: string): { icon: LucideIcon; label: string } {
  const known: Partial<Record<string, { icon: LucideIcon; label: string }>> = STEP_KINDS;
  return known[kind] ?? UNKNOWN_KIND;
}
