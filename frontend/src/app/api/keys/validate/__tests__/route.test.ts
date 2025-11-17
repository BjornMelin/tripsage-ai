/** @vitest-environment node */

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
  getClientIpFromHeaders: vi.fn(() => "127.0.0.1"),
}));
const MOCK_SUPABASE = vi.hoisted(() => ({
  auth: {
    getUser: vi.fn(),
  },
}));
const CREATE_SUPABASE = vi.hoisted(() => vi.fn(async () => MOCK_SUPABASE));
const mockCreateOpenAI = vi.hoisted(() => vi.fn());
const mockCreateAnthropic = vi.hoisted(() => vi.fn());

vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    getClientIpFromHeaders: MOCK_ROUTE_HELPERS.getClientIpFromHeaders,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

vi.mock("@upstash/redis", () => ({
  Redis: {
    fromEnv: vi.fn(() => ({})),
  },
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
  getServerEnvVarWithFallback: vi.fn((key: string) => {
    if (key === "UPSTASH_REDIS_REST_URL" || key === "UPSTASH_REDIS_REST_TOKEN") {
      return "test-value";
    }
    return undefined;
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
    MOCK_ROUTE_HELPERS.getClientIpFromHeaders.mockReturnValueOnce("10.0.0.1");

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

    await POST(req);

    expect(LIMIT_SPY).toHaveBeenCalledWith("anon:10.0.0.1");
  });
});
