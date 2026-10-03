import { groupShortcuts, type Shortcut } from "@/lib/shortcuts/registry";
import { Dialog, Kbd } from "@/ui";

import styles from "./ShortcutHelpDialog.module.css";

export interface ShortcutHelpDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  shortcuts: Shortcut[];
}

export function ShortcutHelpDialog({ open, onOpenChange, shortcuts }: ShortcutHelpDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Keyboard shortcuts">
      {groupShortcuts(shortcuts).map(([group, items]) => (
        <section key={group} className={styles.group} aria-labelledby={`shortcuts-${group}`}>
          <h3 id={`shortcuts-${group}`} className={styles.heading}>
            {group}
          </h3>
          <dl className={styles.list}>
            {items.map((shortcut) => (
              <div key={shortcut.id} className={styles.row}>
                <dt>
                  <Kbd>{shortcut.label}</Kbd>
                </dt>
                <dd>{shortcut.description}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
      <p className={styles.note}>Shortcuts do not apply while typing in a text field.</p>
    </Dialog>
  );
}
