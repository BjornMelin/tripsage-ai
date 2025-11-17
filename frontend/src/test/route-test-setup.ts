/**
 * @fileoverview Shared test setup for Next.js route handler tests.
 * Provides common mocks for cookies, Supabase, Redis, and rate limiting.
 */

import { vi } from "vitest";
import { getMockCookiesForTest } from "./route-helpers";

/**
 * Sets up common mocks for route handler tests.
 * Call this at the top of route test files before any imports.
 *
 * @param options Configuration for mocks.
 */
export function setupRouteTestMocks(
  options: {
    cookies?: Record<string, string>;
    supabaseUser?: { id: string } | null;
    rateLimitSuccess?: boolean;
  } = {}
) {
  const {
    cookies = { "sb-access-token": "test-token" },
    supabaseUser = { id: "user-1" },
    rateLimitSuccess = true,
  } = options;

  // Mock next/headers cookies()
  vi.mock("next/headers", () => ({
    cookies: vi.fn(() => Promise.resolve(getMockCookiesForTest(cookies))),
  }));

  // Mock Supabase server client
  vi.mock("@/lib/supabase/server", () => ({
    createServerSupabase: vi.fn(async () => ({
      auth: {
        getUser: async () => ({
          data: { user: supabaseUser },
          error: supabaseUser ? null : new Error("Unauthorized"),
        }),
      },
    })),
  }));

  // Mock Redis
  vi.mock("@/lib/redis", () => ({
    getRedis: vi.fn(() => Promise.resolve({})),
  }));

  // Mock rate limiting
  vi.mock("@/lib/ratelimit/config", () => ({
    enforceRouteRateLimit: vi.fn(() =>
      Promise.resolve(
        rateLimitSuccess
          ? null
          : {
              error: "rate_limit_exceeded",
              reason: "Too many requests",
              status: 429,
            }
      )
    ),
  }));
}
