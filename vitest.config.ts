/**
 * @fileoverview Vitest configuration optimized for <1 minute test runtime.
 * Key optimizations:
 * - Extends Vitest default excludes (critical for fast discovery)
 * - Uses forks for deterministic worker teardown (avoids Node fetch/threads hangs)
 * - Enables dependency optimization for client only
 * - Disables CSS processing globally
 */

import os from "node:os";
import path from "node:path";
import react from "@vitejs/plugin-react";
import { configDefaults, coverageConfigDefaults, defineConfig } from "vitest/config";

const isCi = process.env.CI === "true" || process.env.CI === "1";

const cpuCount =
  typeof os.availableParallelism === "function"
    ? os.availableParallelism()
    : os.cpus().length;

const maxThreads = isCi
  ? Math.min(4, Math.max(1, Math.floor(cpuCount / 2)))
  : Math.max(1, Math.floor(cpuCount / 2));
// Component tests (jsdom) use more memory - limit concurrency
const maxForks = isCi
  ? cpuCount >= 4
    ? 3
    : 2
  : Math.max(1, Math.min(4, Math.floor(cpuCount / 4)));

export default defineConfig({
  cacheDir: ".vitest-cache",
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@ai": path.resolve(__dirname, "./src/ai"),
      "@domain": path.resolve(__dirname, "./src/domain"),
      "@schemas": path.resolve(__dirname, "./src/domain/schemas"),
      "botid/server": path.resolve(__dirname, "./src/test/mocks/botid-server.ts"),
      "katex/dist/katex.min.css": path.resolve(
        __dirname,
        "./src/test/mocks/empty-css.ts"
      ),
      "rehype-harden": path.resolve(__dirname, "./src/test/mocks/rehype-harden.ts"),
      "rehype-harden/dist/index.js": path.resolve(
        __dirname,
        "./src/test/mocks/rehype-harden.ts"
      ),
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

    coverage: {
      ...coverageConfigDefaults,
      exclude: [
        ...coverageConfigDefaults.exclude,
        "**/dist/**",
        "**/e2e/**",
        "**/*.config.*",
      ],
      provider: "v8",
      reporter: ["text", "json", "lcov"],
      thresholds: {
        // Global baseline thresholds (raise incrementally).
        // See docs/development/testing/coverage-milestones.md for current measurements and raise plan.
        branches: 40,
        functions: 55,
        lines: 50,
        statements: 50,
      },
    },

    // Disable CSS processing globally
    css: false,

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

    // CRITICAL: Extend defaults, do not replace
    exclude: [...configDefaults.exclude, "**/e2e/**", "**/*.e2e.*"],
    globals: true,
    hookTimeout: 3000,
    // Worker limit is pool-agnostic; keep this conservative for Node projects.
    // JSDOM forks are memory-heavy, so that project overrides the worker cap.
    maxWorkers: maxThreads,
    passWithNoTests: false,

    // Prefer forks for compatibility and reliable shutdown across Node + jsdom.
    pool: "forks",

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
          sequence: { groupOrder: 0 },
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
          sequence: { groupOrder: 0 },
        },
      },
      {
        extends: true,
        test: {
          environment: "node",
          include: ["src/app/api/**/*.{test,spec}.?(c|m)[jt]s"],
          name: "api",
          sequence: { groupOrder: 0 },
        },
      },
      {
        extends: true,
        test: {
          environment: "jsdom",
          exclude: [
            "src/app/api/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/__tests__/**/*.integration.{test,spec}.?(c|m)[jt]s?(x)",
            "src/__tests__/**/*.int.{test,spec}.?(c|m)[jt]s?(x)",
            "src/__tests__/**/*-integration.{test,spec}.?(c|m)[jt]s?(x)",
          ],
          include: [
            "src/components/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/app/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/hooks/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/stores/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/__tests__/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*.dom.{test,spec}.?(c|m)[jt]s?(x)",
          ],
          // Forked workers are memory-heavy; keep this capped regardless of CPU count.
          maxWorkers: maxForks,
          name: "component",
          pool: "forks",
          sequence: { groupOrder: 1 },
          setupFiles: ["./src/test/setup-jsdom.ts"],
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
          sequence: { groupOrder: 0 },
        },
      },
    ],

    // Reporters
    reporters: isCi ? ["dot", "github-actions"] : ["default"],
    restoreMocks: true,

    server: {
      deps: {
        // Inline Streamdown so its KaTeX CSS dynamic import is handled by Vitest/Vite
        // even with `test.css: false` (otherwise Node tries to import `.css` directly).
        inline: ["rehype-harden", "streamdown"],
      },
    },

    setupFiles: ["./src/test/setup-node.ts"],
    teardownTimeout: 2000,

    // Timeouts (balanced for speed and reliability)
    testTimeout: 5000,
    unstubEnvs: true,
  },
});
