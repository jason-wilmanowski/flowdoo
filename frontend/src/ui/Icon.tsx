import type { LucideIcon } from "lucide-react";

import styles from "./Icon.module.css";

/** Stroke width of every icon (one icon set, one weight). */
export const ICON_STROKE = 1.5;

export interface IconProps {
  icon: LucideIcon;
  /** 14px instead of 16px, for compact controls. */
  compact?: boolean;
  /** Accessible name; without it the icon is decorative (aria-hidden). */
  label?: string;
  className?: string;
}

export function Icon({ icon: Glyph, compact = false, label, className }: IconProps) {
  return (
    <Glyph
      className={[styles.icon, compact ? styles.compact : "", className ?? ""].join(" ").trim()}
      strokeWidth={ICON_STROKE}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? "img" : undefined}
      focusable={false}
    />
  );
}
