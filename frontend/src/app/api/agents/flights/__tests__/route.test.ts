/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";

vi.mock("@/lib/agents/config-resolver", () => ({
  resolveAgentConfig: vi.fn(async () => ({ config: { model: "gpt-4o-mini" } })),
}));

const mockLimitFn = vi.fn().mockResolvedValue({
  limit: 30,
  remaining: 29,
  reset: Date.now() + 60000,
  success: true,
});
const mockSlidingWindow = vi.fn(() => ({}));
const RATELIMIT_MOCK = vi.fn(function RatelimitMock() {
  return {
    limit: mockLimitFn,
  };
}) as unknown as {
  new (...args: unknown[]): { limit: typeof mockLimitFn };
  slidingWindow: typeof mockSlidingWindow;
};
(RATELIMIT_MOCK as { slidingWindow: typeof mockSlidingWindow }).slidingWindow =
  mockSlidingWindow;

// Mock next/headers cookies() before any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
      }),
    },
  })),
}));

// Mock provider registry
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: {}, modelId: "gpt-4o" })),
}));

// Mock flight agent
vi.mock("@/lib/agents/flight-agent", () => ({
  runFlightAgent: vi.fn(() => ({
    toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => ({})),
}));

// Mock Upstash rate limiter
vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: RATELIMIT_MOCK,
}));

// Mock route helpers
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("/api/agents/flights route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLimitFn.mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60000,
      success: true,
    });
  });

  it("streams when valid and enabled", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: {
        departureDate: "2025-12-15",
        destination: "JFK",
        origin: "SFO",
        passengers: 1,
      },
      method: "POST",
      url: "http://localhost/api/agents/flights",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
  });

  it("returns 429 when the rate limit is exceeded", async () => {
    mockLimitFn.mockResolvedValueOnce({
      limit: 30,
      remaining: 0,
      reset: Date.now() + 60000,
      success: false,
    });

    const mod = await import("../route");
    const req = createMockNextRequest({
      body: {
        departureDate: "2025-12-15",
        destination: "JFK",
        origin: "SFO",
        passengers: 1,
      },
      method: "POST",
      url: "http://localhost/api/agents/flights",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(429);
    const payload = await res.json();
    expect(payload.error).toBe("rate_limit_exceeded");
    expect(mockLimitFn).toHaveBeenCalledTimes(1);
  });
});
