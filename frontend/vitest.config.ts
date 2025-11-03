/**
 * @fileoverview Vitest configuration tuned for stability and CI performance.
 * - Uses forks by default for process isolation; switches to threads in CI.
 * - JSDOM environment for UI tests, type/lint gates run separately.
 */

import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const isCI = process.env.CI === "true" || process.env.CI === "1";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    unstubEnvs: true,
    setupFiles: ["./src/test-setup.ts"],
    include: ["**/*.{test,spec}.ts?(x)"],
    exclude: ["**/node_modules/**", "**/e2e/**", "**/*.e2e.*"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      exclude: ["**/dist/**", "**/e2e/**", "**/*.config.*"],
      thresholds: {
        global: {
          branches: 85,
          functions: 90,
          lines: 90,
          statements: 90,
        },
      },
    },
    // Runtime stability
    isolate: true,
    clearMocks: true,
    restoreMocks: true,
    // Timeouts
    testTimeout: 7500,
    hookTimeout: 12000,
    teardownTimeout: 10000,
    // Stop early on cascading failures in CI
    bail: isCI ? 5 : 0,
    passWithNoTests: true,
    // Pools/workers: default to forks; prefer threads in CI for big suites
    pool: "threads",
    maxWorkers: isCI ? 2 : 1,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Shim Next.js server-only import for tests
      "server-only": path.resolve(__dirname, "./src/test/mocks/server-only.ts"),
    },
  },
});
