import type { ComponentProps } from "react";

import styles from "./Input.module.css";

export interface InputProps extends ComponentProps<"input"> {
  /** Visible label; omit only when an aria-label is given. */
  label?: string;
  compact?: boolean;
  /** Technical values (model, method, ids) in the mono face. */
  mono?: boolean;
}

/** Text input with an optional visible label. */
export function Input({
  label,
  compact = false,
  mono = false,
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
    <label className={styles.field}>
      <span className={styles.label}>{label}</span>
      {input}
    </label>
  );
}
