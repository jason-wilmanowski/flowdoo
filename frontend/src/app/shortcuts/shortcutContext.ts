import { createContext, useContext, useEffect, useRef } from "react";

import type { Shortcut } from "@/lib/shortcuts/registry";

export interface ShortcutContextValue {
  register: (shortcut: Shortcut) => () => void;
  openHelp: () => void;
}

export const ShortcutContext = createContext<ShortcutContextValue | null>(null);

function useShortcutContext(): ShortcutContextValue {
  const context = useContext(ShortcutContext);
  if (!context) throw new Error("Shortcuts are used outside of <ShortcutProvider>");
  return context;
}

/** Register a shortcut while the calling component is mounted. */
export function useShortcut(shortcut: Omit<Shortcut, "run">, run: () => void): void {
  const { register } = useShortcutContext();
  const latestRun = useRef(run);
  useEffect(() => {
    latestRun.current = run;
  });
  const { id, key, label, description, group } = shortcut;
  useEffect(
    () =>
      register({
        id,
        key,
        label,
        description,
        group,
        run: () => {
          latestRun.current();
        },
      }),
    [register, id, key, label, description, group],
  );
}

export function useOpenShortcutHelp(): () => void {
  return useShortcutContext().openHelp;
}
