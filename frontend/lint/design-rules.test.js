// @vitest-environment node
// Proves each visual lint rule: a violating snippet is rejected, the token-based one passes.
import path from "node:path";
import { fileURLToPath } from "node:url";

import { ESLint } from "eslint";
import stylelint from "stylelint";
import tseslint from "typescript-eslint";
import { describe, expect, test } from "vitest";

import { designRules as eslintDesignRules } from "../eslint.design-rules.js";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const configFile = path.join(root, "stylelint.config.js");

async function cssWarnings(code, file = "src/ui/Probe.module.css") {
  const result = await stylelint.lint({ code, codeFilename: path.join(root, file), configFile });
  return result.results[0].warnings.map((w) => w.rule);
}

const eslint = new ESLint({
  cwd: root,
  overrideConfigFile: true,
  overrideConfig: [
    {
      files: ["**/*.tsx"],
      languageOptions: {
        parser: tseslint.parser,
        parserOptions: { ecmaFeatures: { jsx: true } },
      },
      rules: eslintDesignRules,
    },
  ],
});

async function tsxMessages(code) {
  const [result] = await eslint.lintText(code, { filePath: path.join(root, "src/Probe.tsx") });
  return result.messages.map((m) => m.ruleId);
}

describe("stylelint visual rules", () => {
  test.each([
    ["hex color", ".a { color: #1f6feb; }", "color-no-hex"],
    ["named color", ".a { color: red; }", "color-named"],
    ["rgb()", ".a { color: rgb(0 0 0); }", "function-disallowed-list"],
    ["hsl()", ".a { background: hsl(210 50% 50%); }", "function-disallowed-list"],
    [
      "linear gradient",
      ".a { background: linear-gradient(red, blue); }",
      "function-disallowed-list",
    ],
    [
      "radial gradient",
      ".a { background-image: radial-gradient(var(--bg), var(--surface)); }",
      "function-disallowed-list",
    ],
    [
      "conic gradient",
      ".a { background: conic-gradient(var(--bg), var(--surface)); }",
      "function-disallowed-list",
    ],
    ["backdrop-filter", ".a { backdrop-filter: none; }", "property-disallowed-list"],
    ["filter blur", ".a { filter: blur(4px); }", "declaration-property-value-disallowed-list"],
    [
      "raw box-shadow",
      ".a { box-shadow: 0 1px 2px var(--border); }",
      "declaration-property-value-disallowed-list",
    ],
    ["raw font size", ".a { font-size: 14px; }", "declaration-property-value-allowed-list"],
    [
      "font size token outside the scale",
      ".a { font-size: var(--text-xl); }",
      "declaration-property-value-allowed-list",
    ],
    ["raw padding", ".a { padding: 10px; }", "declaration-property-value-allowed-list"],
    [
      "raw margin in a list",
      ".a { margin: var(--space-2) 6px; }",
      "declaration-property-value-allowed-list",
    ],
    ["raw gap", ".a { gap: 1rem; }", "declaration-property-value-allowed-list"],
  ])("rejects %s", async (_name, code, rule) => {
    expect(await cssWarnings(code)).toContain(rule);
  });

  test("accepts token-based styles", async () => {
    const code = `.panel {
  padding: var(--space-3) var(--space-4);
  margin: 0 auto var(--gutter);
  gap: var(--space-2);
  font-size: var(--text-base);
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-overlay);
}

.flat {
  box-shadow: none;
}
`;
    expect(await cssWarnings(code)).toEqual([]);
  });

  test("tokens.css may define raw colors", async () => {
    const code =
      ":root {\n  --accent: #1f6feb;\n  --shadow-overlay: 0 4px 12px rgb(0 0 0 / 12%);\n}\n";
    expect(await cssWarnings(code, "src/styles/tokens.css")).toEqual([]);
  });
});

describe("eslint visual rules", () => {
  test.each([
    ["@mui/material", 'import { Button } from "@mui/material";'],
    ["@chakra-ui/react", 'import { Box } from "@chakra-ui/react";'],
    ["antd", 'import { Table } from "antd";'],
    ["@mantine/core", 'import { Card } from "@mantine/core";'],
    ["@radix-ui/themes", 'import { Theme } from "@radix-ui/themes";'],
  ])("rejects the styled UI kit %s", async (_name, code) => {
    expect(await tsxMessages(code)).toContain("no-restricted-imports");
  });

  test("allows unstyled behavior primitives", async () => {
    expect(await tsxMessages('import * as Tooltip from "@radix-ui/react-tooltip";')).toEqual([]);
  });

  test.each([
    ["inline color", "export const A = () => <div style={{ color: 'var(--text)' }} />;"],
    ["inline background", "export const A = () => <div style={{ backgroundColor: 'white' }} />;"],
    ["hex literal", "export const ACCENT = '#1f6feb';"],
    ["rgb literal", "export const SHADOW = 'rgb(0 0 0 / 10%)';"],
    ["gradient literal", "export const BG = 'linear-gradient(red, blue)';"],
  ])("rejects %s", async (_name, code) => {
    expect(await tsxMessages(code)).toContain("no-restricted-syntax");
  });

  test("allows non-color inline styles (e.g. a resizable panel width)", async () => {
    expect(await tsxMessages("export const A = () => <div style={{ width: 260 }} />;")).toEqual([]);
  });
});
