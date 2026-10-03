import styles from "./Button.module.css";
import type { ButtonVariant } from "./Button";

/** Button look for elements that are not buttons, e.g. a router link that navigates. */
export function buttonClassName(variant: ButtonVariant = "secondary", compact = false): string {
  return [styles.button, styles[variant], compact ? styles.compact : ""].join(" ").trim();
}
