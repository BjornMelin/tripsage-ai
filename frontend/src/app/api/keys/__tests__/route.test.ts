/** @vitest-environment node */

import { createHash } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unstubAllEnvs } from "@/test/env-helpers";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const MOCK_INSERT = vi.hoisted(() => vi.fn());
const MOCK_DELETE = vi.hoisted(() => vi.fn());
const LIMIT_SPY = vi.hoisted(() => vi.fn());
const MOCK_SUPABASE = vi.hoisted(() => ({
  auth: {
    getUser: vi.fn(),
  },
}));
const CREATE_SUPABASE = vi.hoisted(() => vi.fn(async () => MOCK_SUPABASE));
const BUILD_RATE_LIMITER = vi.hoisted(() => vi.fn());
const TELEMETRY_SPY = vi.hoisted(() =>
  vi.fn(
    (
      _name,
      _options,
      execute: (span: { setAttribute: () => void }) => Promise<unknown>
    ) => execute({ setAttribute: vi.fn() })
  )
);

vi.mock("@/lib/supabase/rpc", () => ({
  deleteUserApiKey: MOCK_DELETE,
  insertUserApiKey: MOCK_INSERT,
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE,
}));

vi.mock("@/app/api/keys/_rate-limiter", () => ({
  buildRateLimiter: BUILD_RATE_LIMITER,
  RateLimiterConfigurationError: class RateLimiterConfigurationError extends Error {
    constructor(message: string) {
      super(message);
      this.name = "RateLimiterConfigurationError";
    }
  },
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  withTelemetrySpan: TELEMETRY_SPY,
}));

// Mock route helpers - keep actual functions but mock withRequestSpan
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

/**
 * Helper to hash an IP address for rate limiting tests.
 */
function hashIp(ip: string): string {
  return createHash("sha256").update(ip).digest("hex");
}

describe("/api/keys routes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    unstubAllEnvs();
    CREATE_SUPABASE.mockReset();
    CREATE_SUPABASE.mockResolvedValue(MOCK_SUPABASE);
    LIMIT_SPY.mockReset();
    BUILD_RATE_LIMITER.mockReset();
    BUILD_RATE_LIMITER.mockReturnValue(undefined);
    TELEMETRY_SPY.mockReset();
    MOCK_SUPABASE.auth.getUser.mockReset();
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "test-user" } },
      error: null,
    });
    MOCK_DELETE.mockReset();
    MOCK_INSERT.mockReset();
  });

  it("POST /api/keys returns 500 when rate limiter config is missing in production", async () => {
    const { RateLimiterConfigurationError } = await import(
      "@/app/api/keys/_rate-limiter"
    );
    BUILD_RATE_LIMITER.mockImplementation(() => {
      throw new RateLimiterConfigurationError("Rate limiter config missing");
    });
    vi.stubEnv("NODE_ENV", "production");
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: { apiKey: "test", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req);
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.code).toBe("CONFIGURATION_ERROR");
    vi.unstubAllEnvs();
  });

  it("POST /api/keys returns 400 on invalid body", async () => {
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: {},
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("DELETE /api/keys/[service] deletes key via RPC and returns 204", async () => {
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "u1" } },
      error: null,
    });
    MOCK_DELETE.mockResolvedValue(undefined);
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(res.status).toBe(204);
    expect(MOCK_DELETE).toHaveBeenCalledWith("u1", "openai");
  });

  it("POST /api/keys throttles per user id and returns headers", async () => {
    BUILD_RATE_LIMITER.mockReturnValue({ limit: LIMIT_SPY });
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-123" } },
      error: null,
    });
    LIMIT_SPY.mockResolvedValueOnce({
      limit: 10,
      remaining: 0,
      reset: 123,
      success: false,
    });
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      headers: {},
      method: "POST",
      url: "http://localhost/api/keys",
    });

    const res = await POST(req);

    expect(LIMIT_SPY).toHaveBeenCalledWith("user-123");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("0");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("123");
  });

  it("DELETE /api/keys/[service] throttles per user id and returns headers", async () => {
    BUILD_RATE_LIMITER.mockReturnValue({ limit: LIMIT_SPY });
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-999" } },
      error: null,
    });
    LIMIT_SPY.mockResolvedValueOnce({
      limit: 10,
      remaining: 9,
      reset: 456,
      success: false,
    });
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });

    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });

    expect(LIMIT_SPY).toHaveBeenCalledWith("user-999");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("9");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("456");
    expect(MOCK_DELETE).not.toHaveBeenCalled();
  });

  it("POST /api/keys throttles per IP when user id is missing", async () => {
    BUILD_RATE_LIMITER.mockReturnValue({ limit: LIMIT_SPY });
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null,
    });
    LIMIT_SPY.mockResolvedValueOnce({
      limit: 10,
      remaining: 5,
      reset: 789,
      success: false,
    });
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      headers: {
        "x-forwarded-for": "123.123.123.123",
      },
      method: "POST",
      url: "http://localhost/api/keys",
    });

    const res = await POST(req);

    expect(BUILD_RATE_LIMITER).toHaveBeenCalled();
    // IP should be hashed for rate limiting
    expect(LIMIT_SPY).toHaveBeenCalledWith(hashIp("123.123.123.123"));
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("5");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("789");
  });

  it("POST /api/keys throttles with 'unknown' identifier when no user id or IP", async () => {
    BUILD_RATE_LIMITER.mockReturnValue({ limit: LIMIT_SPY });
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null,
    });
    LIMIT_SPY.mockResolvedValueOnce({
      limit: 10,
      remaining: 3,
      reset: 999,
      success: false,
    });
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/keys",
    });

    const res = await POST(req);

    expect(BUILD_RATE_LIMITER).toHaveBeenCalled();
    expect(LIMIT_SPY).toHaveBeenCalledWith("unknown");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("3");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("999");
  });

  it("POST /api/keys validates request body with Zod schema", async () => {
    MOCK_INSERT.mockResolvedValue(undefined);
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: { apiKey: "", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.code).toBe("BAD_REQUEST");
    expect(MOCK_INSERT).not.toHaveBeenCalled();
  });

  it("POST /api/keys rejects oversized request bodies", async () => {
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      headers: {
        "content-length": "70000", // > 64KB
      },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.code).toBe("BAD_REQUEST");
    expect(body.error).toContain("too large");
  });

  it("POST /api/keys normalizes service names before RPC execution", async () => {
    MOCK_INSERT.mockResolvedValue(undefined);
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: { apiKey: "abc123", service: "  OpenAI  " },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req);
    expect(res.status).toBe(204);
    expect(MOCK_INSERT).toHaveBeenCalledWith("test-user", "openai", "abc123");
  });

  it("wraps Supabase insert RPC in telemetry span without api_key attribute", async () => {
    const spanCalls: Array<Record<string, unknown>> = [];
    TELEMETRY_SPY.mockImplementationOnce((_name, options, execute) => {
      spanCalls.push(options);
      return execute({ setAttribute: vi.fn() });
    });
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: { apiKey: "abc", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req);
    expect(res.status).toBe(204);
    expect(TELEMETRY_SPY).toHaveBeenCalledTimes(1);
    expect(spanCalls[0]?.attributes).toMatchObject({
      "keys.operation": "insert",
      "keys.service": "openai",
      "keys.user_id": "test-user",
      "ratelimit.success": true,
    });
    // Verify api_key is NOT in attributes
    expect(spanCalls[0]?.attributes).not.toHaveProperty("keys.api_key");
  });

  it("still opens telemetry span when delete RPC fails", async () => {
    TELEMETRY_SPY.mockImplementationOnce((_name, _options, run) =>
      run({ setAttribute: vi.fn() })
    );
    MOCK_DELETE.mockRejectedValueOnce(new Error("boom"));
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(res.status).toBe(500);
    expect(TELEMETRY_SPY).toHaveBeenCalledTimes(1);
  });
});
