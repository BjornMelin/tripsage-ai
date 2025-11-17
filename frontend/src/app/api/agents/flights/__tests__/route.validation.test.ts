import { describe, expect, it, vi } from "vitest";
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
  resolveProvider: vi.fn(async () => ({ model: {} })),
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

vi.mock("@/lib/ratelimit/config", () => ({
  enforceRouteRateLimit: vi.fn(() => Promise.resolve(null)),
}));

describe("/api/agents/flights validation", () => {
  it("returns 400 on invalid body", async () => {
    const mod = await import("../route");
    // Missing required fields like origin/destination/departureDate
    const req = createMockNextRequest({
      body: { passengers: 1 },
      method: "POST",
      url: "http://localhost/api/agents/flights",
    });
    const res = await mod.POST(req);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe("invalid_request");
    expect(typeof data.reason).toBe("string");
  });
});
