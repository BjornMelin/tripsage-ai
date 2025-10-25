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
    setupFiles: [
      "./src/test-setup.ts",
    ],
    exclude: ["**/node_modules/**", "**/e2e/**", "**/*.e2e.*", "**/*.spec.*"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      exclude: [
        "node_modules/",
        "src/test-setup.ts",
        "e2e/",
        "**/*.d.ts",
        "**/*.config.*",
        "**/*.test.*",
        "**/*.spec.*",
        "**/dist/**",
        "**/__tests__/**",
        "**/coverage/**",
        "public/**",
        "*.config.ts",
        "*.config.js",
      ],
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
    pool: isCI ? "threads" : "forks",
    maxWorkers: isCI ? 2 : 2,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
