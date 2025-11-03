/**
 * @fileoverview Vitest configuration tuned for stability and CI performance.
 * - Uses forks by default for process isolation; switches to threads in CI.
 * - JSDOM environment for UI tests, type/lint gates run separately.
 */

import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const isCi = process.env.CI === "true" || process.env.CI === "1";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Shim Next.js server-only import for tests
      "server-only": path.resolve(__dirname, "./src/test/mocks/server-only.ts"),
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
    hookTimeout: 12000,
    include: ["**/*.{test,spec}.ts?(x)"],
    // Runtime stability
    isolate: true,
    maxWorkers: isCi ? 2 : 1,
    passWithNoTests: true,
    // Pools/workers: default to forks; prefer threads in CI for big suites
    pool: "threads",
    restoreMocks: true,
    setupFiles: ["./src/test-setup.ts"],
    teardownTimeout: 10000,
    // Timeouts
    testTimeout: 7500,
    unstubEnvs: true,
  },
});
