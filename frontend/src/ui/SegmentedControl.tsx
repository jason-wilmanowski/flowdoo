import { useId } from "react";

import styles from "./SegmentedControl.module.css";

export interface SegmentedOption<Value extends string> {
  value: Value;
  label: string;
}

export interface SegmentedControlProps<Value extends string> {
  /** Accessible name of the group, e.g. "Theme". */
  label: string;
  options: readonly SegmentedOption<Value>[];
  value: Value;
  onChange: (value: Value) => void;
}

/** A small set of exclusive choices as native radio buttons (arrow keys move the choice). */
export function SegmentedControl<Value extends string>({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps<Value>) {
  const name = useId();
  return (
    <div className={styles.segmented} role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <label
          key={option.value}
          className={[styles.option, option.value === value ? styles.checked : ""].join(" ").trim()}
        >
          <input
            type="radio"
            className={styles.radio}
            name={name}
            value={option.value}
            checked={option.value === value}
            onChange={() => {
              onChange(option.value);
            }}
          />
          {option.label}
        </label>
      ))}
    </div>
  );
}
