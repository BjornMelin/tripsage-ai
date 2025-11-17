/** @vitest-environment node */

import type { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  stubRateLimitDisabled,
  stubRateLimitEnabled,
  unstubAllEnvs,
} from "@/test/env-helpers";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const LIMIT_SPY = vi.hoisted(() => vi.fn());
const MOCK_ROUTE_HELPERS = vi.hoisted(() => ({
  getClientIpFromHeaders: vi.fn((_req: NextRequest) => "127.0.0.1"),
}));
const MOCK_SUPABASE = vi.hoisted(() => ({
  auth: {
    getUser: vi.fn(),
  },
}));
const CREATE_SUPABASE = vi.hoisted(() => vi.fn(async () => MOCK_SUPABASE));
const mockCreateOpenAI = vi.hoisted(() => vi.fn());
const mockCreateAnthropic = vi.hoisted(() => vi.fn());
const MOCK_GET_REDIS = vi.hoisted(() =>
  vi.fn<() => Redis | undefined>(() => undefined)
);

vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    getClientIpFromHeaders: MOCK_ROUTE_HELPERS.getClientIpFromHeaders,
    getTrustedRateLimitIdentifier: vi.fn((req: NextRequest) => {
      const ip = MOCK_ROUTE_HELPERS.getClientIpFromHeaders(req);
      // Return "anon:" prefix format for test compatibility
      return ip === "unknown" ? "unknown" : `anon:${ip}`;
    }),
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

vi.mock("@/lib/redis", () => ({
  getRedis: MOCK_GET_REDIS,
}));

vi.mock("@upstash/ratelimit", () => {
  const slidingWindow = vi.fn(() => ({}));
  const ctor = vi.fn(function RatelimitMock() {
    return { limit: LIMIT_SPY };
  }) as unknown as {
    new (...args: unknown[]): { limit: ReturnType<typeof LIMIT_SPY> };
    slidingWindow: (...args: unknown[]) => unknown;
  };
  ctor.slidingWindow = slidingWindow as unknown as (...args: unknown[]) => unknown;
  return {
    Ratelimit: ctor,
    slidingWindow,
  };
});

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE,
}));

vi.mock("@ai-sdk/openai", () => ({
  createOpenAI: mockCreateOpenAI,
}));

vi.mock("@ai-sdk/anthropic", () => ({
  createAnthropic: mockCreateAnthropic,
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn((key: string, fallback?: unknown) => {
    // In test environment, check process.env directly (vi.stubEnv sets process.env)
    if (key === "UPSTASH_REDIS_REST_URL") {
      return process.env.UPSTASH_REDIS_REST_URL || fallback;
    }
    if (key === "UPSTASH_REDIS_REST_TOKEN") {
      return process.env.UPSTASH_REDIS_REST_TOKEN || fallback;
    }
    return fallback;
  }),
}));

type FetchLike = (
  input: Parameters<typeof fetch>[0],
  init?: Parameters<typeof fetch>[1]
) => Promise<Response>;

type MockFetch = ReturnType<typeof vi.fn<FetchLike>>;

function buildProvider(fetchMock: MockFetch, baseUrl = "https://provider.test/") {
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const config = {
    baseURL: normalizedBase,
    fetch: fetchMock,
    headers: vi.fn(() => ({ Authorization: "Bearer test" })),
  };
  const model = { config };
  const providerFn = vi.fn(() => model);
  return Object.assign(providerFn, {});
}

describe("/api/keys/validate route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    unstubAllEnvs();
    stubRateLimitDisabled();
    MOCK_ROUTE_HELPERS.getClientIpFromHeaders.mockReturnValue("127.0.0.1");
    mockCreateOpenAI.mockReset();
    mockCreateAnthropic.mockReset();
    CREATE_SUPABASE.mockReset();
    CREATE_SUPABASE.mockResolvedValue(MOCK_SUPABASE);
    LIMIT_SPY.mockReset();
    LIMIT_SPY.mockResolvedValue({
      limit: 20,
      remaining: 19,
      reset: Date.now() + 60000,
      success: true,
    });
    MOCK_GET_REDIS.mockReset();
    MOCK_GET_REDIS.mockReturnValue(undefined); // Disable rate limiting by default
    MOCK_SUPABASE.auth.getUser.mockReset();
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "u1" } },
      error: null,
    });
    // Ensure Supabase SSR client does not throw when real module is imported
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon-test-key");
  });

  it("returns isValid true on successful provider response", async () => {
    const fetchMock = vi
      .fn<FetchLike>()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    mockCreateOpenAI.mockImplementation(() => buildProvider(fetchMock));

    const { POST } = await import("../route");
    const req = createMockNextRequest({
      body: { apiKey: "sk-test", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys/validate",
    });

    const res = await POST(req);
    const body = await res.json();

    expect(fetchMock).toHaveBeenCalledWith("https://provider.test/models", {
      headers: { Authorization: "Bearer test" },
      method: "GET",
    });
    expect({ body, status: res.status }).toEqual({
      body: { isValid: true },
      status: 200,
    });
  });

  it("returns UNAUTHORIZED when provider denies access", async () => {
    const fetchMock = vi
      .fn<FetchLike>()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 401 }));
    mockCreateOpenAI.mockImplementation(() => buildProvider(fetchMock));

    const { POST } = await import("../route");
    const req = createMockNextRequest({
      body: { apiKey: "sk-test", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys/validate",
    });

    const res = await POST(req);
    const body = await res.json();

    expect({ body, status: res.status }).toEqual({
      body: { isValid: false, reason: "UNAUTHORIZED" },
      status: 200,
    });
  });

  it("returns TRANSPORT_ERROR when request fails", async () => {
    const fetchMock = vi
      .fn<FetchLike>()
      .mockRejectedValue(new TypeError("Failed to fetch"));
    mockCreateOpenAI.mockImplementation(() => buildProvider(fetchMock));

    const { POST } = await import("../route");
    const req = createMockNextRequest({
      body: { apiKey: "sk-test", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys/validate",
    });

    const res = await POST(req);
    const body = await res.json();

    expect({ body, status: res.status }).toEqual({
      body: { isValid: false, reason: "TRANSPORT_ERROR" },
      status: 200,
    });
  });

  it("throttles per user id and returns headers", async () => {
    stubRateLimitEnabled();
    // Return mock Redis instance when rate limiting enabled (getRedis checks env vars via mocked getServerEnvVarWithFallback)
    MOCK_GET_REDIS.mockReturnValue({} as Redis);
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "validate-user" } },
      error: null,
    });
    LIMIT_SPY.mockResolvedValueOnce({
      limit: 20,
      remaining: 0,
      reset: 789,
      success: false,
    });
    const { POST } = await import("@/app/api/keys/validate/route");
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/keys/validate",
    });

    const res = await POST(req);

    expect(LIMIT_SPY).toHaveBeenCalledWith("validate-user");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("20");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("0");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("789");
  });

  it("falls back to client IP when user is missing", async () => {
    stubRateLimitEnabled();
    // Return mock Redis instance when rate limiting enabled (same pattern as working test)
    MOCK_GET_REDIS.mockReturnValue({} as Redis);
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null,
    });
    LIMIT_SPY.mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: 123,
      success: true,
    });
    // Ensure getClientIpFromHeaders returns the expected IP when called
    MOCK_ROUTE_HELPERS.getClientIpFromHeaders.mockReturnValue("10.0.0.1");

    const fetchMock = vi
      .fn<FetchLike>()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    mockCreateOpenAI.mockImplementation(() => buildProvider(fetchMock));

    const { POST } = await import("@/app/api/keys/validate/route");
    const req = createMockNextRequest({
      body: { apiKey: "sk-test", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys/validate",
    });

    await POST(req);

    // Verify rate limiter was called with the expected identifier
    // The identifier should be "anon:10.0.0.1" since user is null
    expect(LIMIT_SPY).toHaveBeenCalled();
    const callArgs = LIMIT_SPY.mock.calls[0];
    expect(callArgs?.[0]).toBe("anon:10.0.0.1");
  });
});
