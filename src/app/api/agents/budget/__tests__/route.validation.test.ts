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
} from "@/test/helpers/route";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

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
  resolveProvider: vi.fn(async () => ({ model: {} })),
}));

// Mock budget agent
vi.mock("@/lib/agents/budget-agent", () => ({
  runBudgetAgent: vi.fn(() => ({
    toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

describe("/api/agents/budget validation", () => {
  beforeEach(() => {
    const mockLimitFn = vi.fn().mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60000,
      success: true,
    });
    setRateLimitFactoryForTests(async (_key, _identifier) => mockLimitFn());
    setSupabaseFactoryForTests(async () =>
      unsafeCast<TypedServerSupabase>({
        auth: {
          getUser: async () => ({
            data: { user: { id: "user-1" } },
            error: null,
          }),
        },
      })
    );
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
  });

  it("returns 400 on invalid body", async () => {
    const mod = await import("../route");
    // Missing required fields like destination/durationDays
    const req = createMockNextRequest({
      body: { travelers: 2 },
      method: "POST",
      url: "http://localhost/api/agents/budget",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe("invalid_request");
    expect(Array.isArray(data.issues)).toBe(true);
  });
});
