/**
 * @fileoverview Unified API route testing utilities for Next.js.
 *
 * Provides:
 * - Request factories (makeJsonRequest, createRouteParamsContext)
 * - Hoisted mocks for withApiGuards dependencies
 * - Auth/cookies/rate-limiting test controls
 */

import type { User } from "@supabase/supabase-js";
import { AuthError } from "@supabase/supabase-js";
import { NextRequest } from "next/server";
import { afterEach, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import type { BotIdVerification } from "@/lib/security/botid";
import { mockBotIdHumanResponse } from "@/test/mocks/botid";
import { createMockSupabaseClient, getSupabaseMockState } from "@/test/mocks/supabase";
import { registerUpstashMocksWithVitest } from "@/test/upstash/setup";
import { getMockCookiesForTest } from "./route";

registerUpstashMocksWithVitest();

// ---- REQUEST FACTORIES ------------------------------------------------------

/**
 * Create a NextRequest with JSON body for API route tests.
 *
 * @param url - Request URL (can be relative or absolute)
 * @param body - Request body (will be JSON stringified)
 * @param init - Optional headers and method overrides
 * @returns NextRequest instance
 *
 * @example
 * ```ts
 * const req = makeJsonRequest("/api/auth/mfa/verify", { code: "123456" });
 * const res = await POST(req, context);
 * ```
 */
export function makeJsonRequest(
  url: string,
  body: unknown,
  init?: { headers?: HeadersInit; method?: string }
): NextRequest {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const method = init?.method ?? "POST";
  const fullUrl = url.startsWith("http") ? url : `http://localhost:3000${url}`;
  return new NextRequest(
    new Request(fullUrl, {
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      headers,
      method,
    })
  );
}

// Re-export from route.ts to avoid duplication
export { createRouteParamsContext } from "./route";

// ---- ROUTE MOCK STATE ------------------------------------------------------

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

const BOT_ID_SPY = vi.hoisted(() =>
  vi.fn(async (): Promise<BotIdVerification> => ({ ...mockBotIdHumanResponse }))
);

// Alias vitest's resolved "botid/server" to allow mockApiRouteBotIdOnce to intercept
vi.mock("botid/server", () => {
  return {
    checkBotId: BOT_ID_SPY,
  };
});

// Create a lazily-initialized Supabase client holder
// The actual client is created after imports are resolved
let supabaseClient: ReturnType<typeof createMockSupabaseClient> | null = null;

const getSupabaseClient = () => {
  if (!supabaseClient) {
    supabaseClient = ensureMfaMock(createMockSupabaseClient({ user: STATE.user }));
    const mockState = getSupabaseMockState(supabaseClient);
    mockState.user = STATE.user;
    // createMockSupabaseClient installs a default getUser spy; this override is
    // intentional so mockApiRouteAuthUser() can update STATE.user at runtime and
    // have auth.getUser() reflect those dynamic changes.
    vi.spyOn(supabaseClient.auth, "getUser").mockImplementation(() => {
      if (STATE.user)
        return Promise.resolve({ data: { user: STATE.user }, error: null });
      return Promise.resolve({
        data: { user: null },
        error: new AuthError("Not authenticated", 401, "no_authorization"),
      });
    });
  }
  return supabaseClient;
};

const CREATE_SUPABASE_MOCK = vi.hoisted(() => vi.fn(async () => getSupabaseClient()));

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
  // Reset Supabase client with current state by resetting the lazy holder
  supabaseClient = null;
  // Recreate the client with current STATE.user
  const client = getSupabaseClient();
  CREATE_SUPABASE_MOCK.mockReset();
  CREATE_SUPABASE_MOCK.mockResolvedValue(client);
  setSupabaseFactoryForTests(async () => client);
  LIMIT_SPY.mockReset();
  LIMIT_SPY.mockResolvedValue({ ...DEFAULT_RATE_LIMIT });
  // Most API route tests should not depend on Redis/Upstash availability.
  // Default to a deterministic allow response unless a test overrides this.
  setRateLimitFactoryForTests(LIMIT_SPY);
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
    if (supabaseClient) getSupabaseMockState(supabaseClient).user = null;
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
    user_metadata: {
      ...baseUser.user_metadata,
      ...(user as User).user_metadata,
    },
  } as User;

  STATE.user = normalizedUser;
  if (supabaseClient) getSupabaseMockState(supabaseClient).user = normalizedUser;
}

// Ensure mfa methods are available on the mocked supabase auth client
const ensureMfaMock = (client: ReturnType<typeof createMockSupabaseClient>) => {
  const mfaUser =
    getSupabaseMockState(client).user ??
    ({
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      app_metadata: {},
      aud: "authenticated",
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      created_at: new Date(0).toISOString(),
      email: "test@example.com",
      id: "test-user",
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      user_metadata: {},
    } as User);

  vi.spyOn(client.auth.mfa, "challenge").mockResolvedValue({
    data: {
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      expires_at: 0,
      id: "challenge-mock",
      type: "totp",
    },
    error: null,
  });
  vi.spyOn(client.auth.mfa, "enroll").mockResolvedValue({
    data: {
      id: "enroll-mock",
      totp: {
        // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
        qr_code: "",
        secret: "",
        uri: "",
      },
      type: "totp",
    },
    error: null,
  });
  vi.spyOn(client.auth.mfa, "getAuthenticatorAssuranceLevel").mockResolvedValue({
    data: {
      currentAuthenticationMethods: [],
      currentLevel: "aal2",
      nextLevel: "aal2",
    },
    error: null,
  });
  vi.spyOn(client.auth.mfa, "listFactors").mockResolvedValue({
    data: { all: [], phone: [], totp: [], webauthn: [] },
    error: null,
  });
  vi.spyOn(client.auth.mfa, "unenroll").mockResolvedValue({
    data: { id: "unenroll-mock" },
    error: null,
  });
  vi.spyOn(client.auth.mfa, "verify").mockResolvedValue({
    data: {
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      access_token: "mock-access-token",
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      expires_in: 3_600,
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      refresh_token: "mock-refresh-token",
      // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
      token_type: "bearer",
      user: getSupabaseMockState(client).user ?? mfaUser,
    },
    error: null,
  });
  return client;
};

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

/**
 * Override the BotID response returned by `checkBotId()` for a single request.
 *
 * @param overrides - BotID response fields to override (merged with mockBotIdHumanResponse defaults)
 */
export function mockApiRouteBotIdOnce(overrides: Partial<BotIdVerification>): void {
  BOT_ID_SPY.mockResolvedValueOnce({ ...mockBotIdHumanResponse, ...overrides });
}

/** Replace the cookie jar returned by mocked `cookies()`. */
export function mockApiRouteCookies(cookies: Record<string, string>): void {
  STATE.cookies = { ...cookies };
}

/** Get the current Supabase client mock (lazy-initialized). */
export const getApiRouteSupabaseMock = () => getSupabaseClient();
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
