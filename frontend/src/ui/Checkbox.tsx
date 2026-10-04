import type { ComponentProps, ReactNode } from "react";

import styles from "./Checkbox.module.css";

export interface CheckboxProps extends Omit<ComponentProps<"input">, "type"> {
  label: ReactNode;
}

/** Native checkbox with its label; the label is part of the click target. */
export function Checkbox({ label, className, ...rest }: CheckboxProps) {
  return (
    <label className={[styles.checkbox, className ?? ""].join(" ").trim()}>
      <input type="checkbox" className={styles.box} {...rest} />
      <span>{label}</span>
    </label>
  );
}
