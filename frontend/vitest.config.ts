/**
 * @fileoverview Vitest configuration tuned for stability and CI performance.
 * - Uses vmForks for consistent process isolation across all environments.
 * - Optimized worker count for multi-core CPUs (local: cpus/2, CI: 2).
 * - JSDOM environment for UI tests, type/lint gates run separately.
 */

import os from "node:os";
import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const isCi = process.env.CI === "true" || process.env.CI === "1";
const cpuCount = os.cpus().length;
const optimalWorkers = isCi ? 2 : Math.max(1, Math.floor(cpuCount / 2));

export default defineConfig({
  ssr: {
    noExternal: ["rehype-harden"],
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Shim Next.js server-only import for tests
      "server-only": path.resolve(__dirname, "./src/test/mocks/server-only.ts"),
      // Shim problematic ESM/CJS package in test runners
      "rehype-harden": path.resolve(
        __dirname,
        "./src/test/mocks/rehype-harden.ts"
      ),
      "rehype-harden/dist/index.js": path.resolve(
        __dirname,
        "./src/test/mocks/rehype-harden.ts"
      ),
    },
  },
  test: {
    // Stop early on cascading failures in CI
    bail: isCi ? 5 : 0,
    clearMocks: true,
    coverage: {
      exclude: ["**/dist/**", "**/e2e/**", "**/*.config.*"],
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      thresholds: {
        global: {
          branches: 85,
          functions: 90,
          lines: 90,
          statements: 90,
        },
      },
    },
    environment: "jsdom",
    exclude: ["**/node_modules/**", "**/e2e/**", "**/*.e2e.*"],
    globals: true,
    hookTimeout: 8000,
    include: ["**/*.{test,spec}.ts?(x)"],
    // Runtime stability
    isolate: true,
    maxWorkers: optimalWorkers,
    passWithNoTests: true,
    // Use VM pool runners so CSS from node_modules is transformed in tests
    // (fixes "Unknown file extension .css" for packages like katex via Streamdown)
    // Use vmForks consistently for stability and predictable behavior
    pool: "vmForks",
    // Ensure Vite transforms CSS imports under vmThreads
    deps: {
      web: {
        transformCss: true,
      },
    },
    server: {
      deps: {
        inline: ["rehype-harden"],
      },
    },
    restoreMocks: true,
    setupFiles: ["./src/test-setup.ts"],
    teardownTimeout: 6000,
    // Timeouts
    testTimeout: 5000,
    unstubEnvs: true,
  },
});
