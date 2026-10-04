import type { ComponentProps } from "react";

import styles from "./Input.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<ComponentProps<"select">, "children"> {
  options: readonly SelectOption[];
  /** Visible label; omit only when an aria-label is given. */
  label?: string;
  compact?: boolean;
}

/** Native select (keyboard and screen reader behavior of the platform) in our style. */
export function Select({ options, label, compact = false, className, ...rest }: SelectProps) {
  const select = (
    <select
      className={[styles.select, compact ? styles.compact : "", className ?? ""].join(" ").trim()}
      {...rest}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
  if (!label) return select;
  return (
    <label className={styles.field}>
      <span className={styles.label}>{label}</span>
      {select}
    </label>
  );
}
