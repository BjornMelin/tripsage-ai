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
    // browser runner is disabled by default
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
      // 'all' moved/unsupported in current @vitest/coverage-v8 types; omit for build
    },
    // Performance optimizations
    // pool option signatures have changed; use defaults for compatibility
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
