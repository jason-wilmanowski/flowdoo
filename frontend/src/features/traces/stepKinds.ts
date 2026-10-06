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

export interface KindInfo {
  icon: LucideIcon;
  label: string;
  /** What the step does to data: create adds, write changes, unlink removes. */
  tone?: "add" | "change" | "remove";
}

/** Fixed icon and label per step kind, the same everywhere in the UI. */
export const STEP_KINDS: Record<StepKind, KindInfo> = {
  method_call: { icon: SquareFunction, label: "method call" },
  orm_create: { icon: Plus, label: "create", tone: "add" },
  orm_write: { icon: Pencil, label: "write", tone: "change" },
  orm_unlink: { icon: Trash2, label: "unlink", tone: "remove" },
  compute: { icon: Calculator, label: "compute" },
  onchange: { icon: RefreshCcw, label: "onchange" },
  constraint: { icon: CircleCheck, label: "constraint" },
  automation: { icon: Workflow, label: "automation" },
  side_effect_blocked: { icon: OctagonX, label: "blocked side effect" },
};

/** Fallback for kinds a newer recorder may add. */
export const UNKNOWN_KIND: KindInfo = { icon: Ban, label: "unknown" };

/** Icon and label of a kind, also for kinds this UI does not know yet. */
export function stepKind(kind: string): KindInfo {
  const known: Partial<Record<string, KindInfo>> = STEP_KINDS;
  return known[kind] ?? UNKNOWN_KIND;
}
