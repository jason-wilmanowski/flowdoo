// Visual rules for all CSS in src/. Colors, sizes and spacing come from the tokens in
// src/styles/tokens.css; that file is the only place allowed to define raw values.
/** @type {import("stylelint").Config} */

// the spacing scale, plus the one gutter between panels
const SPACE = "var\\((?:--space-[1-7]|--gutter)\\)";
const SPACING_VALUE = new RegExp(`^(-?(0|auto|${SPACE}))(\\s+-?(0|auto|${SPACE}))*$`);

export const designRules = {
  // colors only via tokens
  "color-no-hex": true,
  "color-named": "never",
  "function-disallowed-list": [
    "rgb",
    "rgba",
    "hsl",
    "hsla",
    "hwb",
    "lab",
    "lch",
    "oklab",
    "oklch",
    "color",
    "color-mix",
    // no gradients
    "linear-gradient",
    "radial-gradient",
    "conic-gradient",
    "repeating-linear-gradient",
    "repeating-radial-gradient",
    "repeating-conic-gradient",
  ],
  // no frosted glass
  "property-disallowed-list": ["backdrop-filter", "-webkit-backdrop-filter"],
  "declaration-property-value-disallowed-list": {
    filter: ["/blur\\(/"],
    // shadows only for floating overlays, via one token
    "box-shadow": ["/^(?!var\\(--shadow-overlay\\)$|none$).+/"],
  },
  // type scale and spacing only via tokens
  "declaration-property-value-allowed-list": {
    "font-size": ["/^var\\(--text-(xs|sm|base|lg)\\)$/", "inherit"],
    "/^(margin|padding)(-(top|right|bottom|left|block|inline)(-(start|end))?)?$/": [SPACING_VALUE],
    "/^(gap|row-gap|column-gap)$/": [SPACING_VALUE],
  },
};

export default {
  extends: ["stylelint-config-standard"],
  rules: {
    ...designRules,
    // CSS Modules use camelCase class names (styles.stepRow)
    "selector-class-pattern": "^[a-z][a-zA-Z0-9]*$",
    // and :global(...) to reach outside the module, e.g. the theme on <html>
    "selector-pseudo-class-no-unknown": [true, { ignorePseudoClasses: ["global"] }],
  },
  overrides: [
    {
      // the token definitions themselves
      files: ["src/styles/tokens.css"],
      rules: {
        "color-no-hex": null,
        "function-disallowed-list": null,
        "declaration-property-value-allowed-list": null,
        "declaration-property-value-disallowed-list": null,
      },
    },
  ],
};
