/**
 * Global keyboard shortcuts: matching rules as pure functions. Shortcuts are single keys
 * (`event.key`, e.g. "?", " ", "ArrowLeft"); combinations with Ctrl/Meta/Alt belong to the
 * browser and the OS and are never taken. Keys in form controls belong to the control.
 */
export interface Shortcut {
  id: string;
  /** `KeyboardEvent.key` that triggers it. */
  key: string;
  /** How the key is shown in the help, e.g. "?" or "Space". */
  label: string;
  description: string;
  /** Heading in the help dialog, e.g. "General" or "Replay". */
  group: string;
  run: () => void;
}

type KeyEventLike = Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey" | "target">;

/** Keys typed into a form control belong to that control (text, slider, select, checkbox). */
export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement
  );
}

const ACTIVATION_KEYS = new Set([" ", "Enter"]);

/** Space and Enter on a button or link activate it; they must not also run a shortcut. */
function activatesTarget(key: string, target: EventTarget | null): boolean {
  if (!ACTIVATION_KEYS.has(key) || !(target instanceof HTMLElement)) return false;
  return (
    target instanceof HTMLButtonElement ||
    target instanceof HTMLAnchorElement ||
    target.getAttribute("role") === "button"
  );
}

export function shortcutFor(
  event: KeyEventLike,
  shortcuts: Iterable<Shortcut>,
): Shortcut | undefined {
  if (event.ctrlKey || event.metaKey || event.altKey) return undefined;
  if (isEditableTarget(event.target) || activatesTarget(event.key, event.target)) return undefined;
  for (const shortcut of shortcuts) {
    if (shortcut.key === event.key) return shortcut;
  }
  return undefined;
}

/** Shortcuts by group, groups and entries in registration order. */
export function groupShortcuts(shortcuts: Iterable<Shortcut>): [string, Shortcut[]][] {
  const groups = new Map<string, Shortcut[]>();
  for (const shortcut of shortcuts) {
    const group = groups.get(shortcut.group);
    if (group) group.push(shortcut);
    else groups.set(shortcut.group, [shortcut]);
  }
  return [...groups];
}
