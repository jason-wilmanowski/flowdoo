import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useRef, type ReactNode } from "react";

import styles from "./Dialog.module.css";
import { IconButton } from "./IconButton";

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  /** "sheet": a panel along the right edge (settings), instead of a centered dialog. */
  variant?: "dialog" | "sheet";
}

/**
 * Modal dialog (Radix: focus trap, Escape, focus returns to the trigger). Only for blocking
 * or destructive decisions and the shortcut help.
 */
export function Dialog({ open, onOpenChange, title, children, variant = "dialog" }: DialogProps) {
  // Radix returns focus only to a Dialog.Trigger; dialogs opened by a shortcut have none.
  const returnFocusTo = useRef<HTMLElement | null>(null);
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className={styles.overlay} />
        <RadixDialog.Content
          className={variant === "sheet" ? styles.sheet : styles.content}
          aria-describedby={undefined}
          onOpenAutoFocus={() => {
            returnFocusTo.current =
              document.activeElement instanceof HTMLElement ? document.activeElement : null;
          }}
          onCloseAutoFocus={(event) => {
            if (!returnFocusTo.current?.isConnected) return;
            event.preventDefault();
            returnFocusTo.current.focus();
          }}
        >
          <div className={styles.header}>
            <RadixDialog.Title className={styles.title}>{title}</RadixDialog.Title>
            <RadixDialog.Close asChild>
              <IconButton icon={X} label="Close" tooltip={false} compact />
            </RadixDialog.Close>
          </div>
          <div className={styles.body}>{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
