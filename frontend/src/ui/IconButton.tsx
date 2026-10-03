import type { LucideIcon } from "lucide-react";
import type { ComponentProps } from "react";

import buttonStyles from "./Button.module.css";
import { Icon } from "./Icon";
import styles from "./IconButton.module.css";
import { Tooltip } from "./Tooltip";

export interface IconButtonProps extends Omit<ComponentProps<"button">, "children"> {
  icon: LucideIcon;
  /** Accessible name and tooltip text, e.g. "Copy value". Required: icons need words. */
  label: string;
  variant?: "secondary" | "ghost";
  compact?: boolean;
  /** Tooltip off when the label is visible elsewhere. */
  tooltip?: boolean;
}

export function IconButton({
  icon,
  label,
  variant = "ghost",
  compact = false,
  tooltip = true,
  type = "button",
  className,
  ...rest
}: IconButtonProps) {
  const button = (
    <button
      type={type}
      aria-label={label}
      className={[
        buttonStyles.button,
        buttonStyles[variant],
        styles.iconButton,
        compact ? styles.compact : "",
        className ?? "",
      ]
        .join(" ")
        .trim()}
      {...rest}
    >
      <Icon icon={icon} compact={compact} />
    </button>
  );
  return tooltip ? <Tooltip content={label}>{button}</Tooltip> : button;
}
