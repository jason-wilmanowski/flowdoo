import {
  THEME_STORAGE_KEY,
  applyTheme,
  chooseTheme,
  initialTheme,
  storedTheme,
  systemTheme,
  chooseThemeChoice,
  storedChoice,
} from "@/lib/theme";

function media(dark: boolean): Pick<Window, "matchMedia"> {
  return { matchMedia: () => ({ matches: dark }) as MediaQueryList };
}

describe("theme", () => {
  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("follows the system preference without a stored choice", () => {
    expect(systemTheme(media(true))).toBe("dark");
    expect(systemTheme(media(false))).toBe("light");
  });

  it("prefers the stored choice over the system", () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });
    localStorage.setItem(THEME_STORAGE_KEY, "light");

    expect(initialTheme()).toBe("light");
  });

  it("ignores invalid stored values and unavailable storage", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "purple");
    expect(storedTheme()).toBeNull();

    const broken = {
      getItem: () => {
        throw new Error("denied");
      },
    };
    expect(storedTheme(broken)).toBeNull();
  });

  it("applies the theme as data-theme on <html>", () => {
    applyTheme("dark");

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("remembers an explicit choice", () => {
    chooseTheme("dark");

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });
});

describe("theme choice", () => {
  const memory = () => {
    const data = new Map<string, string>();
    return {
      getItem: (key: string) => data.get(key) ?? null,
      setItem: (key: string, value: string) => void data.set(key, value),
      removeItem: (key: string) => void data.delete(key),
    };
  };
  const media = (dark: boolean) => ({
    matchMedia: (query: string) => ({ matches: dark, media: query }) as MediaQueryList,
  });

  it("stores a fixed choice and forgets it for system", () => {
    const storage = memory();
    const root = document.createElement("html");
    expect(chooseThemeChoice("dark", storage, root, media(false))).toBe("dark");
    expect(storedChoice(storage)).toBe("dark");
    expect(chooseThemeChoice("system", storage, root, media(false))).toBe("light");
    expect(storedChoice(storage)).toBe("system");
    expect(root.dataset.theme).toBe("light");
  });
});
