import type { LucideIcon } from "lucide-react";
import type { ComponentProps } from "react";

import styles from "./Button.module.css";
import { Icon } from "./Icon";
import { Spinner } from "./Spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost";

export interface ButtonProps extends ComponentProps<"button"> {
  /** At most one primary button per view region. */
  variant?: ButtonVariant;
  /** 24px instead of 28px. */
  compact?: boolean;
  icon?: LucideIcon;
  /** Shows a spinner, disables the button and sets aria-busy. */
  loading?: boolean;
}

export function Button({
  variant = "secondary",
  compact = false,
  icon,
  loading = false,
  disabled,
  type = "button",
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={[styles.button, styles[variant], compact ? styles.compact : "", className ?? ""]
        .join(" ")
        .trim()}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner compact /> : icon ? <Icon icon={icon} compact={compact} /> : null}
      {children}
    </button>
  );
}
