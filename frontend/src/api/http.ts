import { AppError, errorFromResponse } from "@/api/errors";

export type HttpMethod = "GET" | "POST" | "DELETE";
export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  query?: Record<string, QueryValue>;
  body?: unknown;
  timeoutMs: number;
  signal?: AbortSignal;
}

export type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

export function buildUrl(
  baseUrl: string,
  path: string,
  query?: Record<string, QueryValue>,
): string {
  const url = new URL(path, baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "")
      url.searchParams.set(key, String(value));
  }
  return url.toString();
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

/**
 * One JSON request. Sends only Content-Type (the API's CORS allows nothing else), applies a
 * timeout, and turns every failure into an AppError. Never logs bodies: they can contain
 * data from the user's Odoo.
 */
export async function request<T>(
  fetchFn: FetchLike,
  baseUrl: string,
  method: HttpMethod,
  path: string,
  options: RequestOptions,
): Promise<T> {
  if (options.signal?.aborted) throw new AppError("aborted", "The request was cancelled.");

  const controller = new AbortController();
  // set from the timer callback; an object so the check below is not narrowed away
  const timeout = { fired: false };
  const timer = setTimeout(() => {
    timeout.fired = true;
    controller.abort();
  }, options.timeoutMs);
  const onUserAbort = () => {
    controller.abort();
  };
  options.signal?.addEventListener("abort", onUserAbort, { once: true });

  try {
    let response: Response;
    try {
      response = await fetchFn(buildUrl(baseUrl, path, options.query), {
        method,
        headers: options.body === undefined ? undefined : { "Content-Type": "application/json" },
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: controller.signal,
      });
    } catch (cause) {
      if (timeout.fired) {
        const seconds = Math.round(options.timeoutMs / 1000);
        throw new AppError("timeout", `The API did not answer within ${String(seconds)} s.`, {
          cause,
        });
      }
      if (controller.signal.aborted) {
        throw new AppError("aborted", "The request was cancelled.", { cause });
      }
      throw new AppError(
        "network",
        `Could not reach the API at ${baseUrl}. Is the backend running?`,
        {
          cause,
        },
      );
    }

    const body = await readJson(response);
    if (!response.ok) throw errorFromResponse(response.status, body);
    if (response.status !== 204 && body === undefined) {
      throw new AppError("unexpected", "The API answered without a readable body.", {
        status: response.status,
      });
    }
    return body as T;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", onUserAbort);
  }
}
