import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { shortcutFor, type Shortcut } from "@/lib/shortcuts/registry";

import { ShortcutContext } from "./shortcutContext";
import { ShortcutHelpDialog } from "./ShortcutHelpDialog";

/**
 * The one keydown listener of the app. Components add shortcuts with `useShortcut`; the
 * help dialog (`?`) lists whatever is registered at the moment.
 */
export function ShortcutProvider({ children }: { children: ReactNode }) {
  const registry = useRef(new Map<string, Shortcut>());
  const [shortcuts, setShortcuts] = useState<Shortcut[]>([]);
  const [helpOpen, setHelpOpen] = useState(false);

  const register = useCallback((shortcut: Shortcut) => {
    registry.current.set(shortcut.id, shortcut);
    setShortcuts([...registry.current.values()]);
    return () => {
      if (registry.current.get(shortcut.id) === shortcut) registry.current.delete(shortcut.id);
      setShortcuts([...registry.current.values()]);
    };
  }, []);

  const openHelp = useCallback(() => {
    setHelpOpen(true);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      const shortcut = shortcutFor(event, registry.current.values());
      if (!shortcut) return;
      event.preventDefault();
      shortcut.run();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  useEffect(
    () =>
      register({
        id: "help",
        key: "?",
        label: "?",
        description: "Show keyboard shortcuts",
        group: "General",
        run: () => {
          setHelpOpen((open) => !open);
        },
      }),
    [register],
  );

  const value = useMemo(() => ({ register, openHelp }), [register, openHelp]);
  return (
    <ShortcutContext.Provider value={value}>
      {children}
      <ShortcutHelpDialog open={helpOpen} onOpenChange={setHelpOpen} shortcuts={shortcuts} />
    </ShortcutContext.Provider>
  );
}
