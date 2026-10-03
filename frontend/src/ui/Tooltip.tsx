import * as RadixTooltip from "@radix-ui/react-tooltip";
import type { ReactElement, ReactNode } from "react";

import styles from "./Tooltip.module.css";

/** Delay before a tooltip opens on hover (focus opens it right away). */
export const TOOLTIP_DELAY_MS = 500;

/** Wrap the app once; tooltips share one delay. */
export function TooltipProvider({ children }: { children: ReactNode }) {
  return <RadixTooltip.Provider delayDuration={TOOLTIP_DELAY_MS}>{children}</RadixTooltip.Provider>;
}

export interface TooltipProps {
  content: ReactNode;
  /** One focusable element (button, link). */
  children: ReactElement;
  side?: "top" | "right" | "bottom" | "left";
}

/** Short hint for a control. Not for essential information: that belongs in the UI. */
export function Tooltip({ content, children, side = "bottom" }: TooltipProps) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content className={styles.content} side={side} sideOffset={4}>
          {content}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
