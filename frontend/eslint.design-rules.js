// Rules that keep the UI on its own components and tokens. Shared by eslint.config.js and
// the tests in lint/, so the tests check exactly what CI enforces.

// Component libraries that bring their own look. Unstyled behavior primitives (e.g. Radix
// UI primitives) are fine: they are styled with our tokens.
export const STYLED_UI_KITS = [
  "@mui/*",
  "@material-ui/*",
  "@chakra-ui/*",
  "antd",
  "@ant-design/*",
  "@mantine/*",
  "bootstrap",
  "react-bootstrap",
  "@radix-ui/themes",
  "@nextui-org/*",
  "@heroui/*",
  "semantic-ui-react",
  "primereact",
  "@fluentui/*",
  "@blueprintjs/*",
  "daisyui",
  "flowbite-react",
];

const COLOR_STYLE_KEYS =
  "/^(color|background|backgroundColor|backgroundImage|border(Top|Right|Bottom|Left)?Color|borderColor|outlineColor|fill|stroke|boxShadow|textShadow)$/";

export const designRules = {
  "no-restricted-imports": [
    "error",
    {
      patterns: [
        {
          group: STYLED_UI_KITS,
          message: "Styled UI kits are not used; build on src/ui and the tokens.",
        },
      ],
    },
  ],
  "no-restricted-syntax": [
    "error",
    {
      selector: `JSXAttribute[name.name='style'] Property[key.name=${COLOR_STYLE_KEYS}]`,
      message: "No inline color styles; use a CSS class with tokens.",
    },
    {
      selector: "Literal[value=/^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/]",
      message: "No hardcoded colors; use the tokens in src/styles/tokens.css.",
    },
    {
      selector: "Literal[value=/\\b(rgba?|hsla?|oklch|linear-gradient|radial-gradient)\\(/]",
      message: "No hardcoded colors or gradients; use the tokens in src/styles/tokens.css.",
    },
  ],
};
