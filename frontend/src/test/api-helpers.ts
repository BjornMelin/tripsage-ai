/**
 * @fileoverview Centralized API test helpers.
 *
 * Provides reusable utilities for testing API routes:
 * - Supabase client mocking
 * - Upstash rate limiter mocking
 * - Next.js request mocking
 * - Common API test setup
 */

import type { Ratelimit } from "@upstash/ratelimit";
import { vi } from "vitest";
import { createMockSupabaseClient } from "@/test/mocks/supabase";

/**
 * Create mock Upstash rate limiter.
 *
 * @param shouldLimit - Whether rate limiter should return limit exceeded (default: false)
 * @returns Mock rate limiter instance
 */
export function createMockRateLimiter(
  shouldLimit = false
): InstanceType<typeof Ratelimit> {
  return {
    limit: vi.fn(() =>
      Promise.resolve({
        limit: 10,
        remaining: shouldLimit ? 0 : 10,
        reset: Date.now() + 60000,
        success: !shouldLimit,
      })
    ),
  } as unknown as InstanceType<typeof Ratelimit>;
}

/**
 * Setup common API test mocks.
 * Returns cleanup function.
 *
 * @returns Cleanup function to restore mocks
 */
export function setupApiTestMocks(): () => void {
  const supabaseMock = vi.fn(async () => createMockSupabaseClient());
  const redisEnvMock = vi.fn(() => ({}));

  vi.mock("@/lib/supabase/server", () => ({
    createServerSupabase: supabaseMock,
  }));

  vi.mock("@upstash/redis", () => ({
    // biome-ignore lint/style/useNamingConvention: Redis is a class name from @upstash/redis
    Redis: {
      fromEnv: redisEnvMock,
    },
  }));

  return () => {
    vi.unmock("@/lib/supabase/server");
    vi.unmock("@upstash/redis");
  };
}
