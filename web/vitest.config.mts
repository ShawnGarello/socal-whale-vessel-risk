import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

/**
 * Tests cover the application's non-trivial presentational logic — currently
 * the environment-to-configuration resolution and the load-error formatting in
 * `lib/`. Rendering, the ArcGIS SDK itself, and ArcGIS Online are deliberately
 * not unit-tested; see docs/architecture.md, "Testing boundaries". The map is
 * verified by building it and looking at it in a browser.
 */
export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
});
