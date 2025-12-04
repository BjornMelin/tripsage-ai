/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setSupabaseFactoryForTests } from "@/lib/api/factory";
import { stubRateLimitDisabled } from "@/test/helpers/env";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";
import { setupUpstashMocks } from "@/test/upstash/redis-mock";

const { redis, ratelimit } = setupUpstashMocks();

// Mock next/headers cookies() BEFORE any imports that use it
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
        error: null,
      }),
    },
  })),
}));

// Mock local Redis wrapper to return undefined (skip caching in tests)
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
}));

// Mock AI provider registry
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: "test-model" })),
}));

// Mock AI SDK
vi.mock("ai", () => ({
  generateObject: vi.fn(async () => ({ object: { suggestions: [] } })),
}));

// Import after mocks are set up
import { GET as getSuggestions } from "../suggestions/route";

describe("/api/trips/suggestions route", () => {
  const supabaseClient = {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: { id: "user-1" } },
        error: null,
      })),
    },
  };

  beforeEach(() => {
    setSupabaseFactoryForTests(async () => supabaseClient as never);
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-1" } },
      error: null,
    });
    // Reset Upstash mocks
    redis.__reset?.();
    ratelimit.__reset?.();
  });

  afterEach(() => {
    setSupabaseFactoryForTests(null);
    vi.clearAllMocks();
  });

  it("returns 401 when user is missing", async () => {
    // Disable rate limiting for this test
    stubRateLimitDisabled();

    // Mock unauthenticated user
    supabaseClient.auth.getUser.mockResolvedValueOnce({
      data: { user: null },
      error: new Error("Unauthorized"),
    } as never);

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/suggestions",
    });

    const res = await getSuggestions(req, createRouteParamsContext());

    expect(res.status).toBe(401);
  });

  it("returns suggestions array when generation succeeds", async () => {
    // Disable rate limiting for this test
    stubRateLimitDisabled();

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/suggestions?limit=3",
    });

    const res = await getSuggestions(req, createRouteParamsContext());

    expect(res.status).toBe(200);
    const body = (await res.json()) as unknown[];
    expect(Array.isArray(body)).toBe(true);
  });
});
