/**
 * @fileoverview Vitest configuration optimized for <1 minute test runtime.
 * Key optimizations:
 * - Extends Vitest default excludes (critical for fast discovery)
 * - Uses threads for Node-only projects, forks only for jsdom
 * - Enables dependency optimization for client only
 * - Disables CSS processing globally
 */

import os from "node:os";
import path from "node:path";
import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

const isCi = process.env.CI === "true" || process.env.CI === "1";

const cpuCount =
  typeof os.availableParallelism === "function"
    ? os.availableParallelism()
    : os.cpus().length;

const maxThreads = isCi
  ? Math.min(4, Math.max(1, Math.floor(cpuCount / 2)))
  : Math.max(1, Math.floor(cpuCount / 2));
// Component tests (jsdom) use more memory - limit concurrency
const maxForks = isCi ? 2 : Math.max(1, Math.min(4, Math.floor(cpuCount / 4)));

export default defineConfig({
  plugins: [react()],
  cacheDir: ".vitest-cache",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@ai": path.resolve(__dirname, "./src/ai"),
      "@domain": path.resolve(__dirname, "./src/domain"),
      "@schemas": path.resolve(__dirname, "./src/domain/schemas"),
      "rehype-harden": path.resolve(__dirname, "./src/test/mocks/rehype-harden.ts"),
      "rehype-harden/dist/index.js": path.resolve(__dirname, "./src/test/mocks/rehype-harden.ts"),
      "server-only": path.resolve(__dirname, "./src/test/mocks/server-only.ts"),
    },
  },
  ssr: {
    noExternal: ["rehype-harden"],
  },
  test: {
    // Core settings
    bail: isCi ? 5 : 0,
    clearMocks: true,
    restoreMocks: true,
    unstubEnvs: true,
    globals: true,

    // CRITICAL: Extend defaults, do not replace
    exclude: [...configDefaults.exclude, "**/e2e/**", "**/*.e2e.*"],

    // Disable CSS processing globally
    css: false,

    // Timeouts (balanced for speed and reliability)
    testTimeout: 5000,
    hookTimeout: 3000,
    teardownTimeout: 2000,

    // Default to threads (faster), forks only for jsdom
    pool: "threads",
    // Worker limit is pool-agnostic; set conservatively for threads by default.
    // Fork-based projects must override this to avoid memory pressure.
    maxWorkers: maxThreads,
    poolOptions: {
      threads: {
        minThreads: 1,
        maxThreads,
        execArgv: ["--max-old-space-size=4096"],
      },
      forks: {
        minForks: 1,
        maxForks,
        execArgv: ["--max-old-space-size=4096"],
      },
    },

    // Fixed dependency optimization
    deps: {
      optimizer: {
        client: {
          enabled: true,
          include: [
            "react",
            "react-dom",
            "@testing-library/react",
            "@testing-library/user-event",
            "@testing-library/jest-dom",
          ],
        },
        ssr: {
          enabled: false,
        },
      },
    },

    // Reporters (blob only for sharding)
    reporters: isCi ? ["dot", "github-actions"] : ["default"],

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

    // Projects: schemas, integration, api, component, unit
    projects: [
      {
        extends: true,
        test: {
          environment: "node",
          include: [
            "src/domain/schemas/**/*.{test,spec}.?(c|m)[jt]s",
            "src/ai/tools/schemas/**/*.{test,spec}.?(c|m)[jt]s",
          ],
          isolate: false,
          name: "schemas",
          pool: "threads",
        },
      },
      {
        extends: true,
        test: {
          environment: "node",
          // Prevent overlap with component/ui tests and API route tests (these belong to other projects).
          exclude: [
            "src/app/**",
            "src/components/**",
            "src/hooks/**",
            "src/stores/**",
            "src/__tests__/**",
            "src/app/api/**",
            "src/**/*.dom.{test,spec}.?(c|m)[jt]s?(x)",
          ],
          include: [
            "src/__tests__/**/*.integration.{test,spec}.?(c|m)[jt]s",
            "src/__tests__/**/*.int.{test,spec}.?(c|m)[jt]s",
            "src/__tests__/**/*-integration.{test,spec}.?(c|m)[jt]s",
            "src/domain/**/*.integration.{test,spec}.?(c|m)[jt]s",
            "src/domain/**/*.int.{test,spec}.?(c|m)[jt]s",
            "src/domain/**/*-integration.{test,spec}.?(c|m)[jt]s",
            "src/lib/**/*.integration.{test,spec}.?(c|m)[jt]s",
            "src/lib/**/*.int.{test,spec}.?(c|m)[jt]s",
            "src/lib/**/*-integration.{test,spec}.?(c|m)[jt]s",
            "src/ai/**/*.integration.{test,spec}.?(c|m)[jt]s",
            "src/ai/**/*.int.{test,spec}.?(c|m)[jt]s",
            "src/ai/**/*-integration.{test,spec}.?(c|m)[jt]s",
          ],
          name: "integration",
          pool: "threads",
        },
      },
      {
        extends: true,
        test: {
          environment: "node",
          include: ["src/app/api/**/*.{test,spec}.?(c|m)[jt]s"],
          name: "api",
          pool: "threads",
        },
      },
      {
        extends: true,
        test: {
          environment: "jsdom",
          exclude: ["src/app/api/**/*.{test,spec}.?(c|m)[jt]s?(x)"],
          include: [
            "src/components/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/app/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/hooks/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/stores/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/__tests__/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*.dom.{test,spec}.?(c|m)[jt]s?(x)",
          ],
          name: "component",
          // Forked workers are memory-heavy; keep this capped regardless of CPU count.
          maxWorkers: maxForks,
          setupFiles: ["./src/test/setup-jsdom.ts"],
          pool: "forks",
        },
      },
      {
        extends: true,
        test: {
          environment: "node",
          exclude: [
            "src/domain/schemas/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/ai/tools/schemas/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*.integration.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*.int.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*-integration.{test,spec}.?(c|m)[jt]s?(x)",
            "src/app/api/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/components/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/app/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/hooks/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/stores/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/__tests__/**",
            "src/**/*.dom.{test,spec}.?(c|m)[jt]s?(x)",
          ],
          include: ["src/**/*.{test,spec}.?(c|m)[jt]s"],
          isolate: true,
          name: "unit",
          pool: "threads",
        },
      },
    ],

    server: {
      deps: {
        inline: ["rehype-harden"],
      },
    },

    setupFiles: ["./src/test/setup-node.ts"],
    passWithNoTests: false,
  },
});
