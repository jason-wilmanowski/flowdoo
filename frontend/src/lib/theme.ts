/**
 * Light/dark theme. The initial theme follows `prefers-color-scheme`; once the user picks
 * one, that choice is stored and wins. Applied as `data-theme` on <html>.
 */
export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "flowdoo.theme";

function isTheme(value: unknown): value is Theme {
  return value === "light" || value === "dark";
}

export function storedTheme(storage: Pick<Storage, "getItem"> = localStorage): Theme | null {
  try {
    const value = storage.getItem(THEME_STORAGE_KEY);
    return isTheme(value) ? value : null;
  } catch {
    return null; // storage unavailable (privacy mode): fall back to the system
  }
}

export function systemTheme(media: Pick<Window, "matchMedia"> = window): Theme {
  return media.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function initialTheme(): Theme {
  return storedTheme() ?? systemTheme();
}

export function applyTheme(theme: Theme, root: HTMLElement = document.documentElement): void {
  root.dataset.theme = theme;
}

/** The user's explicit choice: apply and remember it. */
export function chooseTheme(
  theme: Theme,
  storage: Pick<Storage, "setItem"> = localStorage,
  root: HTMLElement = document.documentElement,
): void {
  applyTheme(theme, root);
  try {
    storage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // not persisted; the choice still applies for this session
  }
}
