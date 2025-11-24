/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import type { TypedServerSupabase } from "@/lib/supabase/server";
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

// Mock provider registry
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: {}, modelId: "gpt-4o" })),
}));

// Mock accommodation agent
vi.mock("@/lib/agents/accommodation-agent", () => ({
  runAccommodationAgent: vi.fn(() => ({
    toTextStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
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

describe("/api/agents/accommodations validation", () => {
  beforeEach(() => {
    const mockLimitFn = vi.fn().mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60000,
      success: true,
    });
    setRateLimitFactoryForTests(async (_key, _identifier) => mockLimitFn());
    setSupabaseFactoryForTests(
      async () =>
        ({
          auth: {
            getUser: async () => ({
              data: { user: { id: "user-1" } },
              error: null,
            }),
          },
        }) as unknown as TypedServerSupabase
    );
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
  });

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
