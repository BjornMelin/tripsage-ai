import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

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
vi.mock("@/lib/providers/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: {}, modelId: "gpt-4o" })),
}));

// Mock flight agent
vi.mock("@/lib/agents/flight-agent", () => ({
  runFlightAgent: vi.fn(() => ({
    toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis and rate limiting
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

const mockEnforceRouteRateLimit = vi.fn(
  () =>
    Promise.resolve(null) as ReturnType<
      typeof import("@/lib/ratelimit/config").enforceRouteRateLimit
    >
);
vi.mock("@/lib/ratelimit/config", () => ({
  enforceRouteRateLimit: mockEnforceRouteRateLimit,
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
    mockEnforceRouteRateLimit.mockResolvedValue(null);
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
    const res = await mod.POST(req);
    expect(res.status).toBe(200);
  });

  it("returns 429 when rate limit exceeded", async () => {
    mockEnforceRouteRateLimit.mockResolvedValueOnce({
      error: "rate_limit_exceeded",
      reason: "Too many requests",
      status: 429,
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
    const res = await mod.POST(req);
    expect(res.status).toBe(429);
    const body = await res.json();
    expect(body.error).toBe("rate_limit_exceeded");
  });

  it("uses user ID for rate limiting when authenticated", async () => {
    // Override Supabase mock for this test
    const { createServerSupabase } = await import("@/lib/supabase/server");
    vi.mocked(createServerSupabase).mockResolvedValueOnce({
      auth: {
        getUser: async () => ({
          data: { user: { id: "user-123" } },
        }),
      },
    } as Awaited<ReturnType<typeof createServerSupabase>>);

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
    await mod.POST(req);

    expect(mockEnforceRouteRateLimit).toHaveBeenCalledWith(
      "flightSearch",
      "user-123",
      expect.any(Function)
    );
  });
});
