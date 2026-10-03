/**
 * Global keyboard shortcuts: matching rules as pure functions. Shortcuts are single keys
 * (`event.key`, e.g. "?", " ", "ArrowLeft"); combinations with Ctrl/Meta/Alt belong to the
 * browser and the OS and are never taken.
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

const EDITABLE_INPUT_TYPES = new Set([
  "text",
  "search",
  "email",
  "number",
  "password",
  "tel",
  "url",
  "date",
  "datetime-local",
  "month",
  "time",
  "week",
]);

/** Keys typed into a text field are text, not shortcuts. */
export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  if (target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return true;
  return target instanceof HTMLInputElement && EDITABLE_INPUT_TYPES.has(target.type);
}

export function shortcutFor(
  event: KeyEventLike,
  shortcuts: Iterable<Shortcut>,
): Shortcut | undefined {
  if (event.ctrlKey || event.metaKey || event.altKey) return undefined;
  if (isEditableTarget(event.target)) return undefined;
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
