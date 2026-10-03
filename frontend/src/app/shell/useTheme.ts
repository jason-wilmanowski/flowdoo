import { useState } from "react";

import { chooseTheme, type Theme } from "@/lib/theme";

/** The theme applied on <html> (set before the first render) and a way to change it. */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  );
  return [
    theme,
    (next) => {
      chooseTheme(next);
      setTheme(next);
    },
  ];
}
