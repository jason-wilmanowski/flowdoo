// @vitest-environment node
// Text/background token pairs used by the UI must reach WCAG AA (4.5:1) in both themes.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const css = readFileSync(fileURLToPath(new URL("./tokens.css", import.meta.url)), "utf8");

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`);
  const body = css.slice(start, css.indexOf("\n}", start));
  const tokens: Record<string, string> = {};
  for (const [, name, value] of body.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    if (name && value) tokens[name] = value.trim();
  }
  return tokens;
}

const light = block(":root");
const dark = { ...light, ...block('[data-theme="dark"]') };

function luminance(hex: string): number {
  const full = hex.replace(/^#(\w)(\w)(\w)$/, "#$1$1$2$2$3$3");
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(full.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const SURFACES = ["--bg", "--surface", "--surface-sunken", "--accent-subtle"];
const PAIRS: [fg: string, bg: string][] = [
  // text tokens on every surface, including the selected row
  ...["--text", "--text-muted", "--text-subtle"].flatMap((fg) =>
    SURFACES.map((bg): [string, string] => [fg, bg]),
  ),
  // values in diff rows
  ["--text", "--diff-add-bg"],
  ["--text", "--diff-remove-bg"],
  ["--text", "--diff-change-bg"],
  // accent and status colors used as text (links, labels, badges)
  ...["--accent", "--accent-hover", "--success", "--warning", "--danger"].flatMap((fg) =>
    ["--bg", "--surface"].map((bg): [string, string] => [fg, bg]),
  ),
  // label of a primary button
  ["--surface", "--accent"],
];

describe.each([
  ["light", light],
  ["dark", dark],
])("%s theme", (_name, tokens) => {
  test.each(PAIRS)("%s on %s reaches 4.5:1", (fg, bg) => {
    const a = tokens[fg];
    const b = tokens[bg];
    expect(a, fg).toMatch(/^#[0-9a-f]{3,6}$/);
    expect(b, bg).toMatch(/^#[0-9a-f]{3,6}$/);
    expect(contrast(a!, b!)).toBeGreaterThanOrEqual(4.5);
  });
});

test("the contrast formula matches WCAG reference values", () => {
  expect(contrast("#000", "#fff")).toBeCloseTo(21, 1);
  expect(contrast("#777", "#fff")).toBeCloseTo(4.48, 2);
});
