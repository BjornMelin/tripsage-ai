/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  apiRouteRateLimitSpy,
  enableApiRouteRateLimit,
  mockApiRouteAuthUser,
  mockApiRouteRateLimitOnce,
  resetApiRouteMocks,
} from "@/test/api-route-helpers";
import { unstubAllEnvs } from "@/test/env-helpers";
import { createMockNextRequest, createRouteParamsContext } from "@/test/route-helpers";

const MOCK_INSERT = vi.hoisted(() => vi.fn());
const MOCK_DELETE = vi.hoisted(() => vi.fn());
const TELEMETRY_SPY = vi.hoisted(() =>
  vi.fn(
    (
      _name: string,
      _options: unknown,
      execute: (span: {
        setAttribute: (key: string, value: unknown) => void;
      }) => Promise<unknown>
    ) => execute({ setAttribute: vi.fn() })
  )
);

vi.mock("@/lib/supabase/rpc", () => ({
  deleteUserApiKey: MOCK_DELETE,
  deleteUserGatewayBaseUrl: vi.fn(),
  insertUserApiKey: MOCK_INSERT,
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  sanitizeAttributes: (attrs: unknown) => attrs,
  withTelemetrySpan: TELEMETRY_SPY,
}));

describe("/api/keys routes", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    vi.clearAllMocks();
    unstubAllEnvs();
    mockApiRouteAuthUser({ id: "test-user" });
    MOCK_INSERT.mockReset();
    MOCK_DELETE.mockReset();
    TELEMETRY_SPY.mockReset();
  });

  it("POST /api/keys returns 400 on invalid body", async () => {
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: {},
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
  });

  it("POST /api/keys persists normalized service names", async () => {
    MOCK_INSERT.mockResolvedValue(undefined);
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: { apiKey: "abc123", service: "  OpenAI  " },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(204);
    expect(MOCK_INSERT).toHaveBeenCalledWith("test-user", "openai", "abc123");
  });

  it("POST /api/keys enforces rate limits per user id", async () => {
    enableApiRouteRateLimit();
    mockApiRouteRateLimitOnce({
      limit: 5,
      remaining: 0,
      reset: 999,
      success: false,
    });
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: { apiKey: "key", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req, createRouteParamsContext());
    expect(apiRouteRateLimitSpy).toHaveBeenCalledWith("test-user");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("0");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("999");
  });

  it("POST /api/keys requires authentication", async () => {
    mockApiRouteAuthUser(null);
    const { POST } = await import("@/app/api/keys/route");
    const req = createMockNextRequest({
      body: { apiKey: "abc", service: "openai" },
      method: "POST",
      url: "http://localhost/api/keys",
    });
    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(401);
    expect(MOCK_INSERT).not.toHaveBeenCalled();
  });

  it("DELETE /api/keys/[service] removes stored key", async () => {
    mockApiRouteAuthUser({ id: "user-1" });
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(res.status).toBe(204);
    expect(MOCK_DELETE).toHaveBeenCalledWith("user-1", "openai");
  });

  it("DELETE /api/keys/[service] enforces rate limits", async () => {
    enableApiRouteRateLimit();
    mockApiRouteRateLimitOnce({ remaining: 0, reset: 123, success: false });
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(apiRouteRateLimitSpy).toHaveBeenCalledWith("test-user");
    expect(res.status).toBe(429);
  });

  it("DELETE /api/keys/[service] returns 401 when unauthenticated", async () => {
    mockApiRouteAuthUser(null);
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(res.status).toBe(401);
    expect(MOCK_DELETE).not.toHaveBeenCalled();
  });
});
