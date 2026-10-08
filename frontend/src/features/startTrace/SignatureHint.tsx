import { Plus } from "lucide-react";

import type { EntrypointParameter } from "@/api/types";
import { Icon } from "@/ui";

import type { SignatureState } from "./useEntrypointSignature";
import styles from "./StartTrace.module.css";

/** Parameters that can be passed by name (not *args/**kwargs). */
const NAMED_KINDS = new Set(["positional_or_keyword", "keyword_only"]);

export interface SignatureHintProps {
  state: SignatureState;
  /** Add a parameter to the arguments (kwargs) field. */
  onAddParameter?: (parameter: EntrypointParameter) => void;
}

/**
 * What Odoo knows about the method: where it comes from and which arguments it takes.
 * Named parameters can be added to the arguments with a click.
 */
export function SignatureHint({ state, onAddParameter }: SignatureHintProps) {
  if (state.phase === "idle") {
    return (
      <p className={styles.hint}>Enter model and method to see the parameters Odoo expects.</p>
    );
  }
  if (state.phase === "loading") {
    return <p className={styles.hint}>Looking up the method in Odoo…</p>;
  }
  if (state.phase === "error") {
    return <p className={styles.problem}>{state.error.message}</p>;
  }
  const { signature } = state;
  return (
    <div className={styles.signature} aria-live="polite">
      <p>
        <code>
          {signature.model}.{signature.method}
        </code>{" "}
        from <code>{signature.module ?? "core"}</code>,{" "}
        {signature.model_level
          ? "called on the model (record IDs are not used)"
          : "called on records"}
      </p>
      {signature.summary ? <p className={styles.hint}>{signature.summary}</p> : null}
      {signature.parameters.length > 0 ? (
        <ul className={styles.parameters} aria-label="Parameters">
          {signature.parameters.map((parameter) => {
            const description = (
              <>
                <code>{parameter.name}</code>
                {parameter.annotation ? (
                  <code className={styles.muted}>: {parameter.annotation}</code>
                ) : null}
                {parameter.required ? (
                  <span className={styles.required}>required</span>
                ) : (
                  <code className={styles.muted}> = {parameter.default ?? "None"}</code>
                )}
              </>
            );
            return (
              <li key={parameter.name}>
                {onAddParameter && NAMED_KINDS.has(parameter.kind) ? (
                  <button
                    type="button"
                    className={styles.parameter}
                    aria-label={`Add ${parameter.name} to the arguments`}
                    onClick={() => {
                      onAddParameter(parameter);
                    }}
                  >
                    <Icon icon={Plus} compact />
                    {description}
                  </button>
                ) : (
                  <span className={styles.parameterText}>{description}</span>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className={styles.hint}>No parameters besides the records.</p>
      )}
    </div>
  );
}
