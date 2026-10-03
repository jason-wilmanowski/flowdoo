import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// File watching inside Docker on macOS/Windows needs polling (VITE_USE_POLLING=true).
const usePolling = process.env.VITE_USE_POLLING === "true";
// shared/ (trace schema, fixtures): ../shared locally, /shared in the container.
const sharedDir =
  process.env.FLOWDOO_SHARED_DIR ?? fileURLToPath(new URL("../shared", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@shared": sharedDir,
    },
  },
  server: {
    strictPort: true,
    fs: { allow: [".", sharedDir] },
    watch: usePolling ? { usePolling: true, interval: 300 } : undefined,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: { modules: { classNameStrategy: "non-scoped" } },
  },
});
