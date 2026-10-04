import type { SignatureState } from "./useEntrypointSignature";
import styles from "./StartTrace.module.css";

/** What Odoo knows about the method: where it comes from and which arguments it takes. */
export function SignatureHint({ state }: { state: SignatureState }) {
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
          {signature.parameters.map((parameter) => (
            <li key={parameter.name}>
              <code>{parameter.name}</code>
              {parameter.annotation ? (
                <code className={styles.muted}>: {parameter.annotation}</code>
              ) : null}
              {parameter.required ? (
                <span className={styles.required}> required</span>
              ) : (
                <code className={styles.muted}> = {parameter.default ?? "None"}</code>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.hint}>No parameters besides the records.</p>
      )}
    </div>
  );
}
