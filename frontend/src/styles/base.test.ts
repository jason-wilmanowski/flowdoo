import { readFileSync } from "node:fs";
import { join } from "node:path";

// Vitest runs from frontend/ (CSS ?raw imports are empty in tests, so read the file).
const baseCss = readFileSync(join(process.cwd(), "src/styles/base.css"), "utf8");

describe("base styles", () => {
  // Radix keeps inactive tab panels in the DOM with the hidden attribute. In a browser a
  // class with display: flex beats the user agent's [hidden] rule, so the invisible graph
  // panel took half the height of "Changes over time". jsdom always computes hidden as
  // display: none, so the rule itself is the contract checked here.
  it("forces [hidden] elements out of the layout", () => {
    expect(baseCss).toMatch(/\[hidden\]\s*\{\s*display:\s*none\s*!important;\s*\}/);
  });
});
