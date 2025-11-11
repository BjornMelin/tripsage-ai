/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unstubAllEnvs } from "@/test/env-helpers";

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
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: TELEMETRY_SPY,
}));

describe("/api/keys routes", () => {
  beforeEach(() => {
    vi.resetModules();
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

  it("POST /api/keys returns 400 on invalid body", async () => {
    vi.resetModules();
    const { POST } = await import("@/app/api/keys/route");
    const req = {
      headers: new Headers(),
      json: async () => ({}),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("DELETE /api/keys/[service] deletes key via RPC and returns 204", async () => {
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "u1" } },
      error: null,
    });
    MOCK_DELETE.mockResolvedValue(undefined);
    vi.resetModules();
    const route = await import("@/app/api/keys/[service]/route");
    const req = { headers: new Headers() } as unknown as NextRequest;
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
    vi.resetModules();
    const { POST } = await import("@/app/api/keys/route");
    const req = {
      headers: new Headers(),
      json: vi.fn(),
    } as unknown as NextRequest;

    const res = await POST(req);

    expect(LIMIT_SPY).toHaveBeenCalledWith("user-123");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("0");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("123");
    expect(req.json).not.toHaveBeenCalled();
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
    vi.resetModules();
    const route = await import("@/app/api/keys/[service]/route");
    const req = { headers: new Headers() } as unknown as NextRequest;

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
    vi.resetModules();
    const { POST } = await import("@/app/api/keys/route");
    const req = {
      headers: new Headers({
        "x-forwarded-for": "123.123.123.123",
      }),
      json: vi.fn(),
    } as unknown as NextRequest;

    const res = await POST(req);

    expect(BUILD_RATE_LIMITER).toHaveBeenCalled();
    expect(LIMIT_SPY).toHaveBeenCalledWith("123.123.123.123");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("5");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("789");
    expect(req.json).not.toHaveBeenCalled();
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
    vi.resetModules();
    const { POST } = await import("@/app/api/keys/route");
    const req = {
      headers: new Headers(),
      json: vi.fn(),
    } as unknown as NextRequest;

    const res = await POST(req);

    expect(BUILD_RATE_LIMITER).toHaveBeenCalled();
    expect(LIMIT_SPY).toHaveBeenCalledWith("unknown");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("3");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("999");
    expect(req.json).not.toHaveBeenCalled();
  });

  it("POST /api/keys normalizes service names before RPC execution", async () => {
    MOCK_INSERT.mockResolvedValue(undefined);
    vi.resetModules();
    const { POST } = await import("@/app/api/keys/route");
    const req = {
      headers: new Headers(),
      json: async () => ({ apiKey: "abc123", service: "  OpenAI  " }),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(204);
    expect(MOCK_INSERT).toHaveBeenCalledWith("test-user", "openai", "abc123");
  });

  it("wraps Supabase insert RPC in telemetry span", async () => {
    const spanCalls: Array<Record<string, unknown>> = [];
    TELEMETRY_SPY.mockImplementationOnce((_name, options, execute) => {
      spanCalls.push(options);
      return execute({ setAttribute: vi.fn() });
    });
    vi.resetModules();
    const { POST } = await import("@/app/api/keys/route");
    const req = {
      headers: new Headers(),
      json: async () => ({ apiKey: "abc", service: "openai" }),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(204);
    expect(TELEMETRY_SPY).toHaveBeenCalledTimes(1);
    expect(spanCalls[0]?.attributes).toMatchObject({
      "keys.operation": "insert",
      "keys.service": "openai",
      "keys.user_id": "test-user",
      "ratelimit.success": true,
    });
  });

  it("still opens telemetry span when delete RPC fails", async () => {
    TELEMETRY_SPY.mockImplementationOnce((_name, _options, run) =>
      run({ setAttribute: vi.fn() })
    );
    MOCK_DELETE.mockRejectedValueOnce(new Error("boom"));
    vi.resetModules();
    const route = await import("@/app/api/keys/[service]/route");
    const req = { headers: new Headers() } as unknown as NextRequest;
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(res.status).toBe(500);
    expect(TELEMETRY_SPY).toHaveBeenCalledTimes(1);
  });
});
