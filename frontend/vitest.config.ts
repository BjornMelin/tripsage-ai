/**
 * @fileoverview Vitest configuration with multi-project setup for optimized performance.
 * - Uses projects to split unit, component, API, and integration tests
 * - Pool selection and concurrency controlled via CLI flags (--pool, --maxWorkers)
 * - Defaults to jsdom for component tests (correctness over speed)
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
      // Shim problematic ESM/CJS package in test runners
      "rehype-harden": path.resolve(__dirname, "./src/test/mocks/rehype-harden.ts"),
      "rehype-harden/dist/index.js": path.resolve(
        __dirname,
        "./src/test/mocks/rehype-harden.ts"
      ),
      // Shim Next.js server-only import for tests
      "server-only": path.resolve(__dirname, "./src/test/mocks/server-only.ts"),
    },
  },
  ssr: {
    noExternal: ["rehype-harden"],
  },
  test: {
    // Shared defaults
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
    deps: {
      optimizer: {
        web: {
          enabled: true,
        },
      },
    },
    exclude: ["**/node_modules/**", "**/e2e/**", "**/*.e2e.*"],
    globals: true,
    hookTimeout: 8000,
    include: ["src/**/*.{test,spec}.?(c|m)[jt]s?(x)"],
    passWithNoTests: false,
    restoreMocks: true,
    server: {
      deps: {
        inline: ["rehype-harden"],
      },
    },
    setupFiles: ["./src/test-setup.ts"],
    teardownTimeout: 6000,
    testTimeout: 5000,
    unstubEnvs: true,
    // Pool and parallelism controlled via CLI flags
    // Projects: schemas, integration, api, component, unit (ordered by specificity)
    projects: [
      {
        // Schema tests: pure validation, no DOM, no isolation (most specific)
        extends: true,
        test: {
          name: "schemas",
          include: ["src/lib/schemas/**/*.{test,spec}.?(c|m)[jt]s?(x)"],
          isolate: false,
          environment: "node",
          deps: {
            web: {
              transformCss: false,
            },
          },
        },
      },
      {
        // Integration tests: end-to-end flows (must come before api/component to catch .integration.* files)
        extends: true,
        test: {
          name: "integration",
          include: [
            "src/**/*.integration.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*.int.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*-integration.{test,spec}.?(c|m)[jt]s?(x)",
          ],
          exclude: [
            // Exclude browser-dependent integration tests that need jsdom
            "src/app/__tests__/error-boundaries-integration.test.tsx",
          ],
          environment: "node",
          deps: {
            web: {
              transformCss: false,
            },
          },
        },
      },
      {
        // API route tests: server-side handlers in app/api
        extends: true,
        test: {
          name: "api",
          include: ["src/app/api/**/*.{test,spec}.?(c|m)[jt]s?(x)"],
          environment: "node",
          deps: {
            web: {
              transformCss: false,
            },
          },
        },
      },
      {
        // Component tests: React components, hooks, app pages, stores (jsdom environment)
        extends: true,
        test: {
          name: "component",
          include: [
            "src/components/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/app/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/hooks/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/stores/**/*.{test,spec}.?(c|m)[jt]s?(x)",
          ],
          exclude: ["src/app/api/**/*.{test,spec}.?(c|m)[jt]s?(x)"],
          environment: "jsdom",
          deps: {
            web: {
              transformCss: true,
            },
          },
        },
      },
      {
        // Unit tests: lib utilities, stores, pure functions (catch-all for remaining)
        extends: true,
        test: {
          name: "unit",
          include: ["src/**/*.{test,spec}.?(c|m)[jt]s?(x)"],
          exclude: [
            "src/lib/schemas/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*.integration.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*.int.{test,spec}.?(c|m)[jt]s?(x)",
            "src/**/*-integration.{test,spec}.?(c|m)[jt]s?(x)",
            "src/app/api/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/components/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/app/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/hooks/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            "src/stores/**/*.{test,spec}.?(c|m)[jt]s?(x)",
            // Exclude browser-dependent lib tests that need jsdom
            "src/lib/__tests__/error-service.test.ts",
          ],
          environment: "node",
          deps: {
            web: {
              transformCss: false,
            },
          },
        },
      },
    ],
  },
});
