/**
 * @fileoverview Shared mocks/utilities for Next.js API route tests.
 *
 * Centralizes hoisted mocks for `withApiGuards` dependencies so every route test
 * follows the same contract (cookies first, auth, then rate limiting) per
 * AGENTS.md and Vitest standards documented in `.cursor/rules/vitest.mdc`.
 */

import { vi } from "vitest";
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

const LIMIT_SPY = vi.hoisted(() => vi.fn(async () => ({ ...DEFAULT_RATE_LIMIT })));

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

const createQueryBuilder = () => {
  const builder = {
    eq: vi.fn(() => builder),
    gte: vi.fn(() => builder),
    insert: vi.fn(() => builder),
    limit: vi.fn(async () => ({ data: [], error: null })),
    lte: vi.fn(() => builder),
    order: vi.fn(async () => ({ data: [], error: null })),
    select: vi.fn(() => builder),
    single: vi.fn(async () => ({ data: null, error: null })),
    update: vi.fn(() => builder),
  };
  return builder;
};

const SUPABASE_CLIENT = vi.hoisted(() => ({
  auth: {
    getUser: vi.fn(async () => ({
      data: { user: { id: "test-user" } },
      error: null,
    })),
  },
  from: vi.fn(() => createQueryBuilder()),
}));

const CREATE_SUPABASE_MOCK = vi.hoisted(() => vi.fn(async () => SUPABASE_CLIENT));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE_MOCK,
}));

vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_, __, fn: () => unknown) => fn()),
  };
});

/** Reset shared mocks to their default state (call in `beforeEach`). */
export function resetApiRouteMocks(): void {
  STATE.cookies = { ...DEFAULT_COOKIE_JAR };
  STATE.rateLimitEnabled = false;
  COOKIES_MOCK.mockImplementation(() =>
    Promise.resolve(getMockCookiesForTest(STATE.cookies))
  );
  COOKIES_MOCK.mockClear();
  SUPABASE_CLIENT.auth.getUser.mockReset();
  SUPABASE_CLIENT.auth.getUser.mockResolvedValue({
    data: { user: { id: "test-user" } },
    error: null,
  });
  SUPABASE_CLIENT.from.mockReset();
  SUPABASE_CLIENT.from.mockImplementation(() => createQueryBuilder());
  CREATE_SUPABASE_MOCK.mockReset();
  CREATE_SUPABASE_MOCK.mockResolvedValue(SUPABASE_CLIENT);
  LIMIT_SPY.mockReset();
  LIMIT_SPY.mockResolvedValue({ ...DEFAULT_RATE_LIMIT });
  GET_REDIS_MOCK.mockReset();
  GET_REDIS_MOCK.mockImplementation(() =>
    STATE.rateLimitEnabled ? REDIS_MOCK : undefined
  );
  REDIS_MOCK.evalsha.mockReset();
  REDIS_MOCK.evalsha.mockResolvedValue(REDIS_DEFAULT_EVALSHA_RESULT);
  REDIS_MOCK.get.mockReset();
  REDIS_MOCK.set.mockReset();
}

/** Override the mocked Supabase user returned by `withApiGuards`. */
export function mockApiRouteAuthUser(user: { id: string } | null): void {
  SUPABASE_CLIENT.auth.getUser.mockResolvedValue({
    data: { user },
    error: null,
  } as unknown as Awaited<ReturnType<typeof SUPABASE_CLIENT.auth.getUser>>);
}

/** Enable rate limiting (Redis available). */
export function enableApiRouteRateLimit(): void {
  STATE.rateLimitEnabled = true;
}

/** Disable rate limiting, simulating missing Redis configuration. */
export function disableApiRouteRateLimit(): void {
  STATE.rateLimitEnabled = false;
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
