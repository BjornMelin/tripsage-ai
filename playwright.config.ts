/**
 * @fileoverview Playwright E2E test configuration.
 */

import { defineConfig, devices } from "@playwright/test";

const e2ePort = Number.parseInt(process.env.E2E_PORT ?? "3100", 10);
const baseURL = `http://localhost:${e2ePort}`;

// Default to 1 worker for test stability (tests may share state via mocked APIs).
// Set E2E_WORKERS=50% for CI parallel execution when tests are fully isolated.
const defaultWorkers = process.env.CI ? "50%" : "1";
const workers = process.env.E2E_WORKERS ?? defaultWorkers;

export default defineConfig({
  forbidOnly: !!process.env.CI,
  // Enable full parallelism only when workers > 1 and tests are isolated.
  // Set E2E_FULLY_PARALLEL=true to enable after ensuring test isolation.
  fullyParallel: process.env.E2E_FULLY_PARALLEL === "true",
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],
  reporter: "html",
  retries: process.env.CI ? 2 : 0,
  testDir: "./e2e",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: {
    command: "node scripts/e2e-webserver.mjs",
    env: {
      ...process.env,
      PORT: `${e2ePort}`,
      // Allow dev server to boot in local/e2e without real Supabase credentials.
      NEXT_PUBLIC_SUPABASE_URL:
        process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54329",
      NEXT_PUBLIC_SUPABASE_ANON_KEY:
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "anon-test-key",
      NEXT_TELEMETRY_DISABLED: process.env.NEXT_TELEMETRY_DISABLED ?? "1",
    },
    reuseExistingServer: false,
    url: baseURL,
    timeout: 120_000,
  },
  // Workers accepts number, percentage string ("50%"), or undefined for auto.
  workers: typeof workers === "string" && workers.includes("%") ? workers : Number(workers),
});
