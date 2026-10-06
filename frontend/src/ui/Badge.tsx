import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import styles from "./Badge.module.css";
import { Icon } from "./Icon";

export type BadgeTone = "neutral" | "accent" | "success" | "warning" | "danger";

export interface BadgeProps {
  children: ReactNode;
  /** Color supports the text, never replaces it: the text must say what it means. */
  tone?: BadgeTone;
  icon?: LucideIcon;
  /** Technical identifiers (module names, kinds) in the mono face. */
  mono?: boolean;
  title?: string;
}

export function Badge({ children, tone = "neutral", icon, mono = false, title }: BadgeProps) {
  return (
    <span
      className={[styles.badge, styles[tone], mono ? styles.mono : "", icon ? styles.withIcon : ""]
        .join(" ")
        .trim()}
      title={title}
    >
      {icon ? <Icon icon={icon} compact /> : null}
      <span className={styles.label}>{children}</span>
    </span>
  );
}
