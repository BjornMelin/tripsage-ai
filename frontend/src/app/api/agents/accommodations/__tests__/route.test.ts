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

vi.mock("@/lib/agents/config-resolver", () => ({
  resolveAgentConfig: vi.fn(async () => ({ config: { model: "gpt-4o-mini" } })),
}));

const mockLimitFn = vi.hoisted(() => vi.fn());

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

// Mock accommodation agent
vi.mock("@ai/agents", () => ({
  createAccommodationAgent: vi.fn(() => ({
    agent: {},
    agentType: "accommodationSearch",
    defaultMessages: [{ content: "schema", role: "user" }],
    modelId: "gpt-4o",
  })),
}));

// Mock createAgentUIStreamResponse
const mockCreateAgentUIStreamResponse = vi.hoisted(() =>
  vi.fn(() => new Response("ok", { status: 200 }))
);
vi.mock("ai", () => ({
  createAgentUIStreamResponse: mockCreateAgentUIStreamResponse(),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => ({})),
}));

// Mock route helpers
vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("/api/agents/accommodations route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    mockLimitFn.mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60000,
      success: true,
    });
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
  });

  it("streams when valid and enabled", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: {
        checkIn: "2025-12-15",
        checkOut: "2025-12-19",
        destination: "NYC",
        guests: 2,
      },
      method: "POST",
      url: "http://localhost/api/agents/accommodations",
    });
    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    expect(mockCreateAgentUIStreamResponse).toHaveBeenCalledTimes(1);

    // Assert that createAgentUIStreamResponse was called with expected structure
    expect(mockCreateAgentUIStreamResponse).toHaveBeenCalledWith(
      expect.objectContaining({
        agent: expect.any(Object),
        messages: expect.any(Array),
      })
    );
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
        checkIn: "2025-12-15",
        checkOut: "2025-12-19",
        destination: "NYC",
        guests: 2,
      },
      method: "POST",
      url: "http://localhost/api/agents/accommodations",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(429);
    expect(await res.json()).toEqual({
      error: "rate_limit_exceeded",
      reason: "Too many requests",
    });
    expect(mockLimitFn).toHaveBeenCalledTimes(1);
  });
});
