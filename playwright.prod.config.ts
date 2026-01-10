/**
 * @fileoverview Playwright E2E configuration for production-only security checks.
 */

import { defineConfig, devices } from "@playwright/test";

const e2ePort = Number.parseInt(process.env.E2E_PORT ?? "3200", 10);
const baseURL = `http://localhost:${e2ePort}`;

export default defineConfig({
  forbidOnly: !!process.env.CI,
  projects: [
    {
      name: "chromium",
      testMatch: /csp-nonce\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  reporter: [["html", { open: "never" }]],
  retries: process.env.CI ? 1 : 0,
  testDir: "./e2e",
  use: { baseURL, trace: "on-first-retry" },
  webServer: {
    command: "node scripts/e2e-webserver-prod.mjs",
    env: {
      // Intentionally avoid spreading `process.env` so local placeholder values
      // don't break strict production env validation during the prod CSP check.
      E2E: "1",
      E2E_SKIP_BUILD: process.env.E2E_SKIP_BUILD ?? "0",
      NODE_ENV: "production",
      PORT: `${e2ePort}`,
      NEXT_PUBLIC_SUPABASE_URL: "http://127.0.0.1:54329",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon-test-key",
      // Required-by-schema production secrets (test-only dummy values).
      SUPABASE_JWT_SECRET: "test-supabase-jwt-secret-32chars-minimum!!",
      TELEMETRY_HASH_SECRET: "test-telemetry-hash-placeholder-32chars-minimum!!",
      NEXT_PUBLIC_APP_URL: baseURL,
      NEXT_PUBLIC_SITE_URL: baseURL,
      NEXT_PUBLIC_API_URL: baseURL,
      NEXT_PUBLIC_BASE_URL: baseURL,
      NEXT_TELEMETRY_DISABLED: "1",
    },
    reuseExistingServer: false,
    url: baseURL,
    timeout: 240_000,
  },
  workers: 1,
});
