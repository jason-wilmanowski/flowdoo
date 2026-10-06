import { useState } from "react";

import { chooseThemeChoice, storedChoice, type ThemeChoice } from "@/lib/theme";

/** The theme choice (light, dark or system) and a way to change it. */
export function useThemeChoice(): [ThemeChoice, (choice: ThemeChoice) => void] {
  const [choice, setChoice] = useState<ThemeChoice>(() => storedChoice());
  return [
    choice,
    (next) => {
      chooseThemeChoice(next);
      setChoice(next);
    },
  ];
}
