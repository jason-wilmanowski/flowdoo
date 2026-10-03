import { AppError } from "@/api/errors";

/** Lifecycle of data a store loads. */
export type Phase = "idle" | "loading" | "ready" | "error";

/** Anything thrown by a data source becomes an AppError (unknown errors included). */
export function toAppError(error: unknown): AppError {
  if (error instanceof AppError) return error;
  return new AppError("unexpected", "Something went wrong while loading data.", { cause: error });
}

export function isAbort(error: unknown): boolean {
  return error instanceof AppError && error.kind === "aborted";
}
