/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  apiRouteRateLimitSpy,
  enableApiRouteRateLimit,
  mockApiRouteAuthUser,
  mockApiRouteRateLimitOnce,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";
import { unstubAllEnvs } from "@/test/helpers/env";
import { TEST_USER_ID } from "@/test/helpers/ids";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";

const MOCK_INSERT = vi.hoisted(() => vi.fn());
const MOCK_DELETE = vi.hoisted(() => vi.fn());
const MOCK_DELETE_GATEWAY = vi.hoisted(() => vi.fn());
const MOCK_SPAN = vi.hoisted(() => ({
  addEvent: vi.fn(),
  end: vi.fn(),
  recordException: vi.fn(),
  setAttribute: vi.fn(),
  setStatus: vi.fn(),
}));
const TELEMETRY_SPY = vi.hoisted(() =>
  vi.fn(
    (
      _name: string,
      _options: unknown,
      execute: (span: {
        setAttribute: (key: string, value: unknown) => void;
      }) => Promise<unknown>
    ) => execute(MOCK_SPAN)
  )
);

vi.mock("@/lib/supabase/rpc", () => ({
  deleteUserApiKey: MOCK_DELETE,
  deleteUserGatewayBaseUrl: MOCK_DELETE_GATEWAY,
  insertUserApiKey: MOCK_INSERT,
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordErrorOnActiveSpan: vi.fn(),
  recordErrorOnSpan: vi.fn(),
  recordTelemetryEvent: vi.fn(),
  sanitizeAttributes: (attrs: unknown) => attrs,
  withTelemetrySpan: TELEMETRY_SPY,
}));

describe("/api/keys routes", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    vi.clearAllMocks();
    unstubAllEnvs();
    mockApiRouteAuthUser({ id: TEST_USER_ID });
    enableApiRouteRateLimit();
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
    expect(MOCK_INSERT).toHaveBeenCalledWith(TEST_USER_ID, "openai", "abc123");
  });

  it("POST /api/keys enforces rate limits per user id", async () => {
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
    expect(apiRouteRateLimitSpy).toHaveBeenCalledWith(
      "keys:create",
      "user:bd7662a5eeb41614e720d477abfcb2272e19a8a70a93b7e3bc8560d44ad326e9"
    );
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("5");
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
    mockApiRouteAuthUser({ id: TEST_USER_ID });
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(res.status).toBe(204);
    expect(MOCK_DELETE).toHaveBeenCalledWith(TEST_USER_ID, "openai");
  });

  it("DELETE /api/keys/[service] enforces rate limits", async () => {
    mockApiRouteRateLimitOnce({ remaining: 0, reset: 123, success: false });
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/openai",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(apiRouteRateLimitSpy).toHaveBeenCalledWith(
      "keys:delete",
      "user:bd7662a5eeb41614e720d477abfcb2272e19a8a70a93b7e3bc8560d44ad326e9"
    );
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

  it("DELETE /api/keys/[service] removes gateway key and config", async () => {
    mockApiRouteAuthUser({ id: TEST_USER_ID });
    MOCK_DELETE.mockResolvedValue(undefined);
    MOCK_DELETE_GATEWAY.mockResolvedValue(undefined);
    const route = await import("@/app/api/keys/[service]/route");
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/keys/gateway",
    });
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "gateway" }),
    });
    expect(res.status).toBe(204);
    expect(MOCK_DELETE_GATEWAY).toHaveBeenCalledWith(TEST_USER_ID);
    expect(MOCK_DELETE).toHaveBeenCalledWith(TEST_USER_ID, "gateway");
  });
});
