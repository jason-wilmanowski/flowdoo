/**
 * Every failure of an API call becomes one AppError, whatever the backend or the network did.
 *
 * The backend answers errors in two formats:
 *   {"detail": "<message>"}                          domain errors, shown as they are
 *   {"detail": [{"loc": [...], "msg": "...", ...}]}  422 request validation (FastAPI)
 */
export type AppErrorKind =
  | "http" // the API answered with an error status and a message
  | "validation" // 422: the request did not pass validation
  | "network" // no answer (API down, CORS, offline)
  | "timeout" // no answer in time
  | "aborted" // cancelled by the user
  | "unexpected"; // an answer we cannot read

export interface FieldError {
  /** e.g. "body.entrypoint_model" or "query.limit" */
  path: string;
  message: string;
}

export class AppError extends Error {
  readonly kind: AppErrorKind;
  readonly status: number | null;
  readonly fieldErrors: readonly FieldError[];

  constructor(
    kind: AppErrorKind,
    message: string,
    options: { status?: number | null; fieldErrors?: readonly FieldError[]; cause?: unknown } = {},
  ) {
    super(message, { cause: options.cause });
    this.name = "AppError";
    this.kind = kind;
    this.status = options.status ?? null;
    this.fieldErrors = options.fieldErrors ?? [];
  }
}

interface ValidationItem {
  loc: unknown[];
  msg: string;
}

function isValidationItem(value: unknown): value is ValidationItem {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Record<string, unknown>;
  return Array.isArray(item.loc) && typeof item.msg === "string";
}

/** Turn an error response (status + already parsed body, if any) into an AppError. */
export function errorFromResponse(status: number, body: unknown): AppError {
  const detail =
    typeof body === "object" && body !== null ? (body as { detail?: unknown }).detail : undefined;

  if (typeof detail === "string") {
    return new AppError(status === 422 ? "validation" : "http", detail, { status });
  }
  if (Array.isArray(detail) && detail.every(isValidationItem)) {
    const fieldErrors = detail.map((item) => ({
      path: item.loc.map(String).join("."),
      message: item.msg,
    }));
    const message = fieldErrors.map((e) => `${e.path}: ${e.message}`).join("; ");
    return new AppError("validation", message || "The request is invalid.", {
      status,
      fieldErrors,
    });
  }
  return new AppError("unexpected", `The API answered with HTTP ${String(status)}.`, { status });
}

export function isAppError(value: unknown): value is AppError {
  return value instanceof AppError;
}
