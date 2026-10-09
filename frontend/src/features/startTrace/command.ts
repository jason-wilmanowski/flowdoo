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
  /** Template values of optional arguments (left out when unchanged). */
  defaults: Record<string, unknown> = {},
  /** The method runs on records (known from its signature): ids are required. */
  recordsRequired = false,
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
  else if (recordsRequired && recordIds.length === 0) {
    errors.recordIds = "This method runs on records: enter at least one record ID.";
  }
  const parsed = parseJsonObject(form.kwargs);
  let kwargs: Record<string, unknown> | string = parsed;
  if (typeof parsed === "string") {
    errors.kwargs = parsed;
  } else {
    const sent = argumentsToSend(parsed, defaults);
    if ("error" in sent) errors.kwargs = sent.error;
    else kwargs = sent.kwargs;
  }
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

/**
 * A Python default as JSON: None/True/False, numbers and quoted strings convert; anything
 * else (expressions, objects) becomes null for the user to fill in.
 */
export function jsonFromPythonDefault(python: string | null): unknown {
  if (python === null) return null;
  const text = python.trim();
  if (text === "None") return null;
  if (text === "True") return true;
  if (text === "False") return false;
  if (/^-?\d+(\.\d+)?$/.test(text)) return Number(text);
  const quoted = /^(['"])(.*)\1$/s.exec(text);
  if (quoted) return quoted[2];
  if (text === "{}") return {};
  if (text === "[]" || text === "()") return [];
  return null;
}

/** Value of a required argument in the template; must be replaced before starting. */
export const REQUIRED = "<required>";

/** Parameters that can be passed by name (not *args or **kwargs). */
const NAMED_KINDS = new Set(["positional_or_keyword", "keyword_only"]);

export interface ParameterLike {
  name: string;
  kind: string;
  required: boolean;
  default?: string | null;
}

export interface KwargsTemplate {
  /** JSON text for the arguments field. */
  text: string;
  /** Optional arguments and the value they start with; unchanged ones are not sent. */
  defaults: Record<string, unknown>;
}

/**
 * Every argument the method takes by name: required ones with the REQUIRED placeholder,
 * optional ones with their default (None as null).
 */
export function kwargsTemplate(parameters: readonly ParameterLike[]): KwargsTemplate {
  const values: Record<string, unknown> = {};
  const defaults: Record<string, unknown> = {};
  for (const parameter of parameters) {
    if (!NAMED_KINDS.has(parameter.kind)) continue;
    if (parameter.required) {
      values[parameter.name] = REQUIRED;
    } else {
      const value = jsonFromPythonDefault(parameter.default ?? null);
      values[parameter.name] = value;
      defaults[parameter.name] = value;
    }
  }
  return {
    text: Object.keys(values).length > 0 ? JSON.stringify(values, null, 2) : "",
    defaults,
  };
}

const sameJson = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/**
 * The arguments to send: required placeholders must be filled in; optional arguments
 * still at their template value are left out, so Odoo uses its own default.
 */
export function argumentsToSend(
  kwargs: Record<string, unknown>,
  defaults: Record<string, unknown>,
): { kwargs: Record<string, unknown> } | { error: string } {
  const missing = Object.keys(kwargs).filter((name) => kwargs[name] === REQUIRED);
  if (missing.length > 0) {
    return {
      error: `Fill in the required ${missing.length === 1 ? "argument" : "arguments"}: ${missing.join(", ")}.`,
    };
  }
  const sent: Record<string, unknown> = {};
  for (const [name, value] of Object.entries(kwargs)) {
    if (name in defaults && sameJson(value, defaults[name])) continue;
    sent[name] = value;
  }
  return { kwargs: sent };
}
