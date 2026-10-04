import type { StartTraceCommand } from "@/api/types";

/** What the user typed in the start dialog, as text. */
export interface StartForm {
  model: string;
  method: string;
  recordIds: string;
  kwargs: string;
  context: string;
  /** true = commit the run in Odoo (dangerous). */
  commit: boolean;
}

export const EMPTY_FORM: StartForm = {
  model: "",
  method: "",
  recordIds: "",
  kwargs: "",
  context: "",
  commit: false,
};

export type FormErrors = Partial<Record<keyof StartForm, string>>;

const IDENTIFIER = /^[a-z_][a-z0-9_.]*$/i;

/** "1, 2 3" -> [1, 2, 3]; empty -> []. */
export function parseRecordIds(text: string): number[] | string {
  const parts = text.split(/[\s,;]+/).filter(Boolean);
  const ids: number[] = [];
  for (const part of parts) {
    if (!/^\d+$/.test(part) || Number(part) <= 0) {
      return `"${part}" is not a record ID. Use positive whole numbers, e.g. 1, 2.`;
    }
    ids.push(Number(part));
  }
  return ids;
}

/** Empty -> {}; otherwise a JSON object. */
export function parseJsonObject(text: string): Record<string, unknown> | string {
  if (!text.trim()) return {};
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch (error) {
    return `Not valid JSON: ${error instanceof Error ? error.message : String(error)}`;
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return 'Must be a JSON object, e.g. {"vals": {"name": "New name"}}.';
  }
  return value as Record<string, unknown>;
}

export function buildCommand(
  form: StartForm,
): { command: StartTraceCommand; errors?: never } | { command?: never; errors: FormErrors } {
  const errors: FormErrors = {};
  const model = form.model.trim();
  const method = form.method.trim();
  if (!model) errors.model = "Enter a model, e.g. sale.order.";
  else if (!IDENTIFIER.test(model)) errors.model = `"${model}" is not a model name.`;
  if (!method) errors.method = "Enter a method, e.g. action_confirm.";
  else if (!IDENTIFIER.test(method) || method.includes(".")) {
    errors.method = `"${method}" is not a method name.`;
  }
  const recordIds = parseRecordIds(form.recordIds);
  if (typeof recordIds === "string") errors.recordIds = recordIds;
  const kwargs = parseJsonObject(form.kwargs);
  if (typeof kwargs === "string") errors.kwargs = kwargs;
  const context = parseJsonObject(form.context);
  if (typeof context === "string") errors.context = context;

  if (
    Object.keys(errors).length > 0 ||
    typeof recordIds === "string" ||
    typeof kwargs === "string" ||
    typeof context === "string"
  ) {
    return { errors };
  }
  return {
    command: {
      entrypoint_model: model,
      entrypoint_method: method,
      record_ids: recordIds,
      kwargs,
      context,
      dry_run: !form.commit,
    },
  };
}

/** The form for a command, to run the same entrypoint again. */
export function formFromCommand(command: StartTraceCommand): StartForm {
  const json = (value: Record<string, unknown> | undefined) =>
    value && Object.keys(value).length > 0 ? JSON.stringify(value, null, 2) : "";
  return {
    model: command.entrypoint_model,
    method: command.entrypoint_method,
    recordIds: command.record_ids.join(", "),
    kwargs: json(command.kwargs),
    context: json(command.context),
    commit: !command.dry_run,
  };
}
