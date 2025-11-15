/**
 * @fileoverview Vitest configuration tuned for stability and CI performance.
 * - Defaults to threads pool for speed; guardrail env can force forks.
 * - Scales workers by available CPUs; env override supported.
 * - Splits into projects: node env for API/server tests, jsdom for UI.
*/

import os from "node:os";
import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const isCi = process.env.CI === "true" || process.env.CI === "1";
const forceForks = process.env.CI_FORCE_FORKS === "1";
const selectedPool = (process.env.VITEST_POOL || (forceForks ? "forks" : "threads")) as
  | "threads"
  | "forks"
  | "vmThreads"
  | "vmForks";
// Prefer availableParallelism when present (Node 18+), fall back to cpus
// Keep at least 1 worker; on CI, avoid exhausting all cores
const cores = (os as any).availableParallelism?.() ?? os.cpus().length;
// In CI, clamp concurrency aggressively to avoid memory pressure from jsdom + V8 coverage.
const ciDefaultWorkers = Math.max(1, Math.min(2, cores));
const defaultWorkers = isCi ? ciDefaultWorkers : Math.max(1, Math.floor(cores / 2));
const optimalWorkers = Number(process.env.VITEST_MAX_WORKERS || defaultWorkers);

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
      reporter: ["text", "json", "lcov"],
      thresholds: {
        global: {
          branches: 85,
          functions: 90,
          lines: 90,
          statements: 90,
        },
      },
    },
    exclude: ["**/node_modules/**", "**/e2e/**", "**/*.e2e.*"],
    globals: true,
    hookTimeout: 8000,
    include: ["**/*.{test,spec}.ts?(x)"],
    // Runtime stability
    isolate: true,
    maxWorkers: optimalWorkers,
    // Optional: when using vm-based pools, recycle workers before they grow too large.
    // Has effect only for `vmThreads` / `vmForks` pools.
    vmMemoryLimit: isCi ? "512MB" : undefined,
    passWithNoTests: true,
    // Default to threads for speed; can be overridden via env or per-project
    pool: selectedPool,
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
    environment: "jsdom",
  },
});
