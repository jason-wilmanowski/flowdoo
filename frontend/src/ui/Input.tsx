import type { ComponentProps } from "react";

import styles from "./Input.module.css";

export interface InputProps extends ComponentProps<"input"> {
  /** Visible label; omit only when an aria-label is given. */
  label?: string;
  compact?: boolean;
  /** Technical values (model, method, ids) in the mono face. */
  mono?: boolean;
  /** Label above the input instead of beside it (forms). */
  stacked?: boolean;
}

/** Text input with an optional visible label. */
export function Input({
  label,
  compact = false,
  mono = false,
  stacked = false,
  className,
  id,
  ...rest
}: InputProps) {
  const input = (
    <input
      id={id}
      className={[
        styles.input,
        compact ? styles.compact : "",
        mono ? styles.mono : "",
        className ?? "",
      ]
        .join(" ")
        .trim()}
      {...rest}
    />
  );
  if (!label) return input;
  return (
    <label className={stacked ? styles.stacked : styles.field}>
      <span className={styles.label}>{label}</span>
      {input}
    </label>
  );
}

export interface TextAreaProps extends ComponentProps<"textarea"> {
  label?: string;
  /** JSON and other technical text in the mono face. */
  mono?: boolean;
}

/** Multi-line variant of Input, e.g. for JSON arguments. */
export function TextArea({ label, mono = false, className, rows = 3, ...rest }: TextAreaProps) {
  const area = (
    <textarea
      rows={rows}
      className={[styles.input, styles.textArea, mono ? styles.mono : "", className ?? ""]
        .join(" ")
        .trim()}
      {...rest}
    />
  );
  if (!label) return area;
  return (
    <label className={styles.stacked}>
      <span className={styles.label}>{label}</span>
      {area}
    </label>
  );
}
