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
  resolveProvider: vi.fn(async () => ({ model: {} })),
}));

// Mock budget agent
vi.mock("@/lib/agents/budget-agent", () => ({
  runBudgetAgent: vi.fn(() => ({
    toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis and rate limiting
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

vi.mock("@/lib/ratelimit/config", () => ({
  enforceRouteRateLimit: vi.fn(() => Promise.resolve({ success: true })),
}));

describe("/api/agents/budget route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("streams when valid and enabled", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: {
        destination: "Tokyo",
        durationDays: 7,
        travelers: 2,
      },
      method: "POST",
      url: "http://localhost/api/agents/budget",
    });
    const res = await mod.POST(req);
    expect(res.status).toBe(200);
  });
});
