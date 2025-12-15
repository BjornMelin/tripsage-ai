/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setSupabaseFactoryForTests } from "@/lib/api/factory";
import { POPULAR_ROUTES_CACHE_KEY_GLOBAL } from "@/lib/flights/popular-routes-cache";
import { stubRateLimitDisabled } from "@/test/helpers/env";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";
import { setupUpstashMocks } from "@/test/upstash/redis-mock";

const { redis, ratelimit } = setupUpstashMocks();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => new Map()),
}));

// Mock @/lib/redis to return raw values (matches real Upstash behavior for getCachedJson)
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => ({
    get: async (key: string) => redis.store.get(key)?.value ?? null,
    set: (key: string, value: string) => {
      redis.store.set(key, { value });
      return "OK";
    },
  })),
}));

// Import after mocks are registered
import { GET as getPopularRoutes } from "../popular-routes/route";

describe("/api/flights/popular-routes", () => {
  const supabaseClient = {
    auth: {
      getUser: vi.fn(),
    },
    from: vi.fn(),
  } as {
    auth: { getUser: ReturnType<typeof vi.fn> };
    from: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    stubRateLimitDisabled();
    redis.__reset?.();
    ratelimit.__reset?.();
    setSupabaseFactoryForTests(async () => supabaseClient as never);
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null,
    });
    supabaseClient.from.mockReset();
  });

  afterEach(() => {
    setSupabaseFactoryForTests(null);
    vi.clearAllMocks();
  });

  it("returns cached routes when present", async () => {
    // Seed cache directly in the shared store (getCachedJson expects raw JSON string)
    redis.store.set(POPULAR_ROUTES_CACHE_KEY_GLOBAL, {
      value: JSON.stringify([
        { date: "May 1, 2026", destination: "Paris", origin: "NYC", price: 123 },
      ]),
    });

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/flights/popular-routes",
    });

    const res = await getPopularRoutes(req, createRouteParamsContext());
    const body = (await res.json()) as unknown;

    expect(res.status).toBe(200);
    expect(body).toEqual([
      { date: "May 1, 2026", destination: "Paris", origin: "NYC", price: 123 },
    ]);
  });

  it("falls back to global routes when cache is empty", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/flights/popular-routes",
    });

    const res = await getPopularRoutes(req, createRouteParamsContext());
    const body = (await res.json()) as Array<{ origin: string; destination: string }>;

    expect(res.status).toBe(200);
    expect(body.some((route) => route.origin === "New York")).toBe(true);
  });
});
