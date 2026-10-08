import { useEffect, useRef, useState } from "react";

import type { AppError } from "@/api/errors";
import type { EntrypointSignature } from "@/api/types";
import type { DataSource } from "@/datasource";
import { isAbort, toAppError } from "@/stores/async";

/** Wait this long after typing before asking Odoo for the signature. */
export const SIGNATURE_DELAY_MS = 400;

export type SignatureState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "ready"; signature: EntrypointSignature }
  | { phase: "error"; error: AppError };

/**
 * Parameters of model.method from the connected Odoo, looked up while the user types.
 * `onLoaded` runs once per signature that arrives (e.g. to prefill the arguments).
 */
export function useEntrypointSignature(
  source: DataSource,
  model: string,
  method: string,
  onLoaded?: (signature: EntrypointSignature) => void,
) {
  const [state, setState] = useState<SignatureState>({ phase: "idle" });
  const latestOnLoaded = useRef(onLoaded);
  useEffect(() => {
    latestOnLoaded.current = onLoaded;
  });
  const ready = model.trim() !== "" && method.trim() !== "";

  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setState({ phase: "loading" });
      source
        .describeEntrypoint(model.trim(), method.trim(), { signal: controller.signal })
        .then((signature) => {
          setState({ phase: "ready", signature });
          latestOnLoaded.current?.(signature);
        })
        .catch((error: unknown) => {
          if (!isAbort(error)) setState({ phase: "error", error: toAppError(error) });
        });
    }, SIGNATURE_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [source, model, method, ready]);

  return ready ? state : ({ phase: "idle" } as const);
}
