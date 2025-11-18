/**
 * @fileoverview Centralized API test helpers.
 *
 * Provides reusable utilities for testing API routes:
 * - Supabase client mocking
 * - Upstash rate limiter mocking
 * - Next.js request mocking
 * - Common API test setup
 */

import type { SupabaseClient } from "@supabase/supabase-js";
import type { Ratelimit } from "@upstash/ratelimit";
import type { NextRequest } from "next/server";
import { vi } from "vitest";

/**
 * Create mock Supabase client for testing.
 *
 * @param overrides - Partial Supabase client to override defaults
 * @returns Mock Supabase client
 */
export function createMockSupabase(
  overrides: Partial<SupabaseClient> = {}
): SupabaseClient {
  return {
    auth: {
      getUser: vi.fn(() =>
        Promise.resolve({
          data: { user: { email: "test@example.com", id: "user-1" } },
          error: null,
        })
      ),
      ...overrides.auth,
    },
    from: vi.fn(() => ({
      delete: vi.fn(() => ({ data: null, error: null })),
      insert: vi.fn(() => ({ data: null, error: null })),
      select: vi.fn(() => ({ data: [], error: null })),
      update: vi.fn(() => ({ data: null, error: null })),
    })),
    ...overrides,
  } as unknown as SupabaseClient;
}

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
 * Mock Next.js request object.
 *
 * @param options - Request configuration options
 * @returns Mock NextRequest object
 */
export function createMockRequest(
  options: {
    method?: string;
    url?: string;
    headers?: Record<string, string>;
    body?: unknown;
    searchParams?: Record<string, string>;
  } = {}
): NextRequest {
  const url = new URL(options.url || "http://localhost:3000/api/test");

  if (options.searchParams) {
    Object.entries(options.searchParams).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  }

  return {
    headers: new Headers(options.headers || {}),
    json: vi.fn(() => Promise.resolve(options.body || {})),
    method: options.method || "GET",
    url: url.toString(),
  } as unknown as NextRequest;
}

/**
 * Setup common API test mocks.
 * Returns cleanup function.
 *
 * @returns Cleanup function to restore mocks
 */
export function setupApiTestMocks(): () => void {
  const supabaseMock = vi.fn(() => createMockSupabase());
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
