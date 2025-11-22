/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";

// Mock next/headers cookies() before any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    checkAuthentication: vi.fn(async () => ({
      error: null,
      isAuthenticated: true,
      user: { id: "user-1" },
    })),
    getTrustedRateLimitIdentifier: vi.fn(() => "anon:test"),
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
        error: null,
      }),
    },
  })),
}));

// Mock provider registry
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: {} })),
}));

// Mock accommodation agent
vi.mock("@/lib/agents/accommodation-agent", () => ({
  runAccommodationAgent: vi.fn(() => ({
    toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

describe("/api/agents/accommodations validation", () => {
  it("returns 400 on invalid body", async () => {
    const mod = await import("../route");
    // Missing required fields like destination/checkIn/checkOut
    const req = createMockNextRequest({
      body: { guests: 2 },
      method: "POST",
      url: "http://localhost/api/agents/accommodations",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe("invalid_request");
    expect(typeof data.reason).toBe("string");
  });
});
