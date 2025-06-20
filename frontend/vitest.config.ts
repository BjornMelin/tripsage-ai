import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    exclude: ["**/node_modules/**", "**/e2e/**", "**/*.e2e.*", "**/*.spec.*"],
    // Enable browser mode for advanced testing
    browser: {
      enabled: false, // Can be enabled for specific tests
      name: "chromium",
      provider: "playwright",
      headless: true,
    },
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
      all: true,
    },
    // Performance optimizations
    pool: "forks",
    poolOptions: {
      forks: {
        singleFork: true, // Better for memory-constrained environments
      },
    },
    isolate: true, // Ensure test isolation
    clearMocks: true, // Clear all mocks between tests
    restoreMocks: true, // Restore original implementations
    // Better error handling
    logHeapUsage: true,
    passWithNoTests: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
