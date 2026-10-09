import { useEffect, useState, type SubmitEvent } from "react";
import { useNavigate } from "react-router";
import { useStore } from "zustand";

import { useStores } from "@/app/appContext";
import { Button, Checkbox, Dialog, Input, Spinner, TextArea } from "@/ui";

import {
  buildCommand,
  EMPTY_FORM,
  kwargsTemplate,
  REQUIRED,
  type FormErrors,
  type KwargsTemplate,
  type StartForm,
} from "./command";
import { SignatureHint } from "./SignatureHint";
import styles from "./StartTrace.module.css";
import { useEntrypointSignature } from "./useEntrypointSignature";

export interface StartTraceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Prefill, e.g. from the trace that is shown. */
  initial?: StartForm;
}

/** Runs an entrypoint in the connected Odoo (a dry run unless chosen otherwise). */
export function StartTraceDialog({ open, onOpenChange, initial }: StartTraceDialogProps) {
  const { source, currentTrace } = useStores();
  const run = useStore(currentTrace, (state) => state.run);
  const start = useStore(currentTrace, (state) => state.start);
  const cancelStart = useStore(currentTrace, (state) => state.cancelStart);
  const dismissRunError = useStore(currentTrace, (state) => state.dismissRunError);
  const navigate = useNavigate();
  const [form, setForm] = useState<StartForm>(initial ?? EMPTY_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  // the arguments the method takes, as last filled in; replaced only while untouched
  const [template, setTemplate] = useState<KwargsTemplate | null>(null);
  const signature = useEntrypointSignature(source, form.model, form.method, (loaded) => {
    const next = kwargsTemplate(loaded.parameters);
    setForm((current) =>
      current.kwargs.trim() === "" || current.kwargs === template?.text
        ? { ...current, kwargs: next.text }
        : current,
    );
    setTemplate(next);
  });
  const running = run.phase === "running";
  const modelLevel = signature.phase === "ready" && signature.signature.model_level;

  // an error from an earlier attempt does not belong to this one
  useEffect(() => {
    dismissRunError();
  }, [dismissRunError]);

  const set = <K extends keyof StartForm>(key: K, value: StartForm[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = buildCommand(
      modelLevel ? { ...form, recordIds: "" } : form,
      template?.defaults ?? {},
      signature.phase === "ready" && !signature.signature.model_level,
    );
    if (result.errors) {
      setErrors(result.errors);
      return;
    }
    void start(result.command).then((trace) => {
      if (!trace) return;
      onOpenChange(false);
      void navigate(`/traces/${trace.id}`);
    });
  };

  const close = (next: boolean) => {
    if (!next && running) cancelStart();
    onOpenChange(next);
  };

  const fieldError = (key: keyof StartForm) =>
    errors[key] ? (
      <span className={styles.problem} role="alert">
        {errors[key]}
      </span>
    ) : null;

  return (
    <Dialog open={open} onOpenChange={close} title="Start a trace">
      <form className={styles.form} onSubmit={submit} noValidate>
        <div className={styles.row}>
          <div className={styles.field}>
            <Input
              stacked
              label="Model"
              mono
              placeholder="sale.order"
              autoComplete="off"
              value={form.model}
              disabled={running}
              aria-invalid={Boolean(errors.model)}
              onChange={(event) => {
                set("model", event.target.value);
              }}
            />
            {fieldError("model")}
          </div>
          <div className={styles.field}>
            <Input
              stacked
              label="Method"
              mono
              placeholder="action_confirm"
              autoComplete="off"
              value={form.method}
              disabled={running}
              aria-invalid={Boolean(errors.method)}
              onChange={(event) => {
                set("method", event.target.value);
              }}
            />
            {fieldError("method")}
          </div>
        </div>

        <SignatureHint state={signature} />

        <div className={styles.field}>
          <Input
            stacked
            label="Record IDs"
            mono
            placeholder={modelLevel ? "not used for this method" : "1, 2"}
            autoComplete="off"
            value={modelLevel ? "" : form.recordIds}
            disabled={running || modelLevel}
            aria-invalid={Boolean(errors.recordIds)}
            onChange={(event) => {
              set("recordIds", event.target.value);
            }}
          />
          {fieldError("recordIds")}
        </div>

        <div className={styles.field}>
          <TextArea
            label="Arguments (kwargs, JSON object)"
            mono
            placeholder='{"vals": {"name": "New name"}}'
            value={form.kwargs}
            disabled={running}
            aria-invalid={Boolean(errors.kwargs)}
            onChange={(event) => {
              set("kwargs", event.target.value);
            }}
          />
          {fieldError("kwargs")}
          {template && template.text ? (
            <span className={styles.hint}>
              Every argument the method takes. Replace <code>"{REQUIRED}"</code>; optional ones left
              at their default (<code>null</code> = None) are not sent.
            </span>
          ) : null}
        </div>

        <div className={styles.field}>
          <TextArea
            label="Context (JSON object)"
            mono
            rows={2}
            placeholder='{"lang": "en_US"}'
            value={form.context}
            disabled={running}
            aria-invalid={Boolean(errors.context)}
            onChange={(event) => {
              set("context", event.target.value);
            }}
          />
          {fieldError("context")}
        </div>

        <div className={form.commit ? styles.commitWarning : styles.dryRunNote}>
          <Checkbox
            label={
              form.commit ? (
                <>
                  <strong>Not a dry run:</strong> the changes are committed in the Odoo database and
                  cannot be undone by Flowdoo. Only for development databases.
                </>
              ) : (
                "Commit the changes in Odoo instead of rolling them back (not a dry run)"
              )
            }
            checked={form.commit}
            disabled={running}
            onChange={(event) => {
              set("commit", event.target.checked);
            }}
          />
        </div>

        {run.phase === "error" && run.error ? (
          <div className={styles.runError} role="alert">
            <p>
              <strong>The run could not be recorded:</strong> {run.error.message}
            </p>
            {run.error.fieldErrors.length > 0 ? (
              <ul>
                {run.error.fieldErrors.map((item) => (
                  <li key={`${item.path}-${item.message}`}>
                    <code>{item.path}</code>: {item.message}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        <div className={styles.actions}>
          {running ? (
            <>
              <Spinner label="Recording in Odoo. This can take up to two minutes." />
              <Button variant="ghost" onClick={cancelStart}>
                Stop waiting
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="ghost"
                onClick={() => {
                  close(false);
                }}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary">
                {form.commit ? "Run and commit" : "Start dry run"}
              </Button>
            </>
          )}
        </div>
      </form>
    </Dialog>
  );
}
