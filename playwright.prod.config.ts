/**
 * @fileoverview Playwright E2E configuration for production-only security checks.
 */

import { defineConfig, devices } from "@playwright/test";

const e2ePort = Number.parseInt(process.env.E2E_PORT ?? "3200", 10);
const e2eHost = "127.0.0.1";
const baseUrl = `http://${e2eHost}:${e2ePort}`;

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
  use: { baseURL: baseUrl, trace: "on-first-retry" },
  webServer: {
    command: "node scripts/e2e-webserver-prod.mjs",
    env: {
      // Intentionally avoid spreading `process.env` so local placeholder values
      // don't break strict production env validation during the prod CSP check.
      APP_BASE_URL: baseUrl,
      E2E: "1",
      E2E_SKIP_BUILD: process.env.E2E_SKIP_BUILD ?? "0",
      // Required-by-schema production secrets (test-only dummy values).
      HMAC_SECRET: "test-hmac-secret-placeholder-32chars-minimum!!",
      HOSTNAME: e2eHost,
      MFA_BACKUP_CODE_PEPPER: "test-mfa-backup-code-placeholder-pepper",
      NEXT_PUBLIC_API_URL: baseUrl,
      NEXT_PUBLIC_APP_URL: baseUrl,
      NEXT_PUBLIC_BASE_URL: baseUrl,
      NEXT_PUBLIC_SITE_URL: baseUrl,
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "publishable-test-key",
      NEXT_PUBLIC_SUPABASE_URL: "http://127.0.0.1:54329",
      NEXT_TELEMETRY_DISABLED: "1",
      NODE_ENV: "production",
      PORT: `${e2ePort}`,
      QSTASH_CURRENT_SIGNING_KEY: "test-qstash-current-signing-key-placeholder",
      QSTASH_NEXT_SIGNING_KEY: "test-qstash-next-signing-key-placeholder",
      SUPABASE_JWT_SECRET: "placeholder-supabase-jwt-secret-32chars-minimum!!",
      TELEMETRY_HASH_SECRET: "test-telemetry-hash-placeholder-32chars-minimum!!",
    },
    reuseExistingServer: false,
    timeout: 240_000,
    url: baseUrl,
  },
  workers: 1,
});
