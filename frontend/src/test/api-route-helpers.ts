/**
 * @fileoverview Shared mocks/utilities for Next.js API route tests.
 *
 * Centralizes hoisted mocks for `withApiGuards` dependencies so every route test
 * follows the same contract (cookies first, auth, then rate limiting) per
 * AGENTS.md and Vitest standards documented in `.cursor/rules/vitest.mdc`.
 */

import type { User } from "@supabase/supabase-js";
import { afterEach, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import { createMockSupabaseClient } from "@/test/mocks/supabase";
import { getMockCookiesForTest } from "@/test/route-helpers";

type RateLimitResult = {
  limit: number;
  remaining: number;
  reset: number;
  success: boolean;
};

const DEFAULT_COOKIE_JAR = { "sb-access-token": "test-token" } as Record<
  string,
  string
>;
const DEFAULT_RATE_LIMIT: RateLimitResult = {
  limit: 60,
  remaining: 59,
  reset: Date.now() + 60_000,
  success: true,
};

const STATE = vi.hoisted(() => ({
  cookies: {} as Record<string, string>,
  rateLimitEnabled: false,
  user: {
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    app_metadata: {},
    aud: "authenticated",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    created_at: new Date(0).toISOString(),
    email: "test@example.com",
    id: "test-user",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    user_metadata: {},
  } as User | null,
}));
STATE.cookies = { ...DEFAULT_COOKIE_JAR };

const COOKIES_MOCK = vi.hoisted(() =>
  vi.fn(() => Promise.resolve(getMockCookiesForTest(STATE.cookies)))
);

vi.mock("next/headers", () => ({
  cookies: COOKIES_MOCK,
}));

const REDIS_DEFAULT_EVALSHA_RESULT = { success: true };

const REDIS_MOCK = vi.hoisted(() => ({
  evalsha: vi.fn(async () => REDIS_DEFAULT_EVALSHA_RESULT),
  get: vi.fn(),
  set: vi.fn(),
}));

const GET_REDIS_MOCK = vi.hoisted(() =>
  vi.fn(() => (STATE.rateLimitEnabled ? REDIS_MOCK : undefined))
);

vi.mock("@/lib/redis", () => ({
  getRedis: GET_REDIS_MOCK,
}));

const LIMIT_SPY = vi.hoisted(() =>
  vi.fn(async (_key: string, _identifier: string) => ({ ...DEFAULT_RATE_LIMIT }))
);

const RATELIMIT_CTOR = vi.hoisted(() => {
  const ctor = vi.fn(function MockRatelimit() {
    return {
      limit: LIMIT_SPY,
    };
  });
  (ctor as unknown as { slidingWindow: ReturnType<typeof vi.fn> }).slidingWindow =
    vi.fn(() => ({}));
  return ctor;
});

vi.mock("@upstash/ratelimit", () => ({
  // biome-ignore lint/style/useNamingConvention: mimic Upstash exported constructor name.
  Ratelimit: RATELIMIT_CTOR,
}));

const SUPABASE_CLIENT = vi.hoisted(() => {
  const client = createMockSupabaseClient({ user: STATE.user });
  // Override auth.getUser to use STATE.user
  client.auth.getUser = vi.fn(() => {
    if (STATE.user) {
      return Promise.resolve({ data: { user: STATE.user }, error: null });
    }
    return Promise.resolve({ data: { user: null }, error: null });
  }) as typeof client.auth.getUser;
  return client;
});

const CREATE_SUPABASE_MOCK = vi.hoisted(() => vi.fn(async () => SUPABASE_CLIENT));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE_MOCK,
}));

vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_, __, fn: () => unknown) => fn()),
  };
});

/** Reset shared mocks to their default state (call in `beforeEach`). */
export function resetApiRouteMocks(): void {
  STATE.cookies = { ...DEFAULT_COOKIE_JAR };
  STATE.user = {
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    app_metadata: {},
    aud: "authenticated",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    created_at: new Date(0).toISOString(),
    email: "test@example.com",
    id: "test-user",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    user_metadata: {},
  } as User;
  STATE.rateLimitEnabled = false;
  COOKIES_MOCK.mockImplementation(() =>
    Promise.resolve(getMockCookiesForTest(STATE.cookies))
  );
  COOKIES_MOCK.mockClear();
  // Reset and recreate Supabase client with current state
  const newClient = createMockSupabaseClient({ user: STATE.user });
  newClient.auth.getUser = vi.fn(() => {
    if (STATE.user) {
      return Promise.resolve({ data: { user: STATE.user }, error: null });
    }
    return Promise.resolve({ data: { user: null }, error: null });
  }) as typeof newClient.auth.getUser;
  Object.assign(SUPABASE_CLIENT, newClient);
  CREATE_SUPABASE_MOCK.mockReset();
  CREATE_SUPABASE_MOCK.mockResolvedValue(SUPABASE_CLIENT);
  setSupabaseFactoryForTests(
    async () =>
      SUPABASE_CLIENT as unknown as Awaited<
        ReturnType<typeof import("@/lib/supabase/server").createServerSupabase>
      >
  );
  LIMIT_SPY.mockReset();
  LIMIT_SPY.mockResolvedValue({ ...DEFAULT_RATE_LIMIT });
  setRateLimitFactoryForTests(null);
  GET_REDIS_MOCK.mockReset();
  GET_REDIS_MOCK.mockImplementation(() =>
    STATE.rateLimitEnabled ? REDIS_MOCK : undefined
  );
  REDIS_MOCK.evalsha.mockReset();
  REDIS_MOCK.evalsha.mockResolvedValue(REDIS_DEFAULT_EVALSHA_RESULT);
  REDIS_MOCK.get.mockReset();
  REDIS_MOCK.set.mockReset();
}

/**
 * Override the mocked Supabase user returned by `withApiGuards`.
 *
 * Accepts partial user objects for convenience in tests and merges them with a
 * fully-populated default user to satisfy Supabase's required fields.
 *
 * @param user - The user to inject or null to simulate unauthenticated.
 */
export function mockApiRouteAuthUser(user: User | null | Partial<User>): void {
  if (!user) {
    STATE.user = null;
    return;
  }

  const baseUser: User = {
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case fields
    app_metadata: {},
    aud: "authenticated",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case fields
    created_at: new Date(0).toISOString(),
    email: "test@example.com",
    id: "test-user",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case fields
    user_metadata: {},
  };

  const normalizedUser = {
    ...baseUser,
    ...user,
    // Explicitly merge metadata objects to preserve defaults
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case fields
    app_metadata: { ...baseUser.app_metadata, ...(user as User).app_metadata },
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case fields
    user_metadata: { ...baseUser.user_metadata, ...(user as User).user_metadata },
  } as User;

  STATE.user = normalizedUser;
}

/** Enable rate limiting (Redis available). */
export function enableApiRouteRateLimit(): void {
  STATE.rateLimitEnabled = true;
  setRateLimitFactoryForTests((key, identifier) => LIMIT_SPY(key, identifier));
}

/** Disable rate limiting, simulating missing Redis configuration. */
export function disableApiRouteRateLimit(): void {
  STATE.rateLimitEnabled = false;
  setRateLimitFactoryForTests(null);
}

/**
 * Configure the next rate limit evaluation result.
 * Set `success` to false to return 429 responses from `withApiGuards`.
 */
export function mockApiRouteRateLimitOnce(overrides: Partial<RateLimitResult>): void {
  LIMIT_SPY.mockResolvedValueOnce({ ...DEFAULT_RATE_LIMIT, ...overrides });
}

/** Replace the cookie jar returned by mocked `cookies()`. */
export function mockApiRouteCookies(cookies: Record<string, string>): void {
  STATE.cookies = { ...cookies };
}

export const apiRouteSupabaseMock = SUPABASE_CLIENT;
export const apiRouteRateLimitSpy = LIMIT_SPY;
export const apiRouteCookiesMock = COOKIES_MOCK;
export const apiRouteCreateSupabaseMock = CREATE_SUPABASE_MOCK;
export const apiRouteRedisMock = REDIS_MOCK;

/** Override the next redis.evalsha response returned to Upstash rate limiters. */
export function mockApiRouteRedisEvalshaOnce(result: RateLimitResult): void {
  REDIS_MOCK.evalsha.mockResolvedValueOnce(result);
}

// Ensure Supabase factory resets between tests to avoid cross-suite leakage.
afterEach(() => {
  setSupabaseFactoryForTests(null);
});
