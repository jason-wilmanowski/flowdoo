import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@/styles/tokens.css";
import "@/styles/base.css";

import { App } from "@/app/App";
import { applyTheme, initialTheme } from "@/lib/theme";

// Before the first render, so the page never flashes in the wrong theme.
applyTheme(initialTheme());

const root = document.getElementById("root");
if (!root) throw new Error("#root element missing in index.html");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
