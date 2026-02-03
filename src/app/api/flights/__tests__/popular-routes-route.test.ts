/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import { POPULAR_ROUTES_CACHE_KEY_GLOBAL } from "@/lib/flights/popular-routes-cache";
import { stubRateLimitDisabled } from "@/test/helpers/env";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";
import { createMockSupabaseClient } from "@/test/mocks/supabase";
import {
  RedisMockClient,
  setupUpstashMocks,
  type UpstashMemoryStore,
} from "@/test/upstash/redis-mock";

const { redis, ratelimit } = setupUpstashMocks();

class RawStringRedisMock extends RedisMockClient {
  constructor(private readonly rawStore: UpstashMemoryStore) {
    super(rawStore);
  }

  override get<T = unknown>(key: string): Promise<T | null> {
    const entry = this.rawStore.get(key);
    if (!entry) return Promise.resolve(null);
    return Promise.resolve(entry.value as T);
  }
}

vi.mock("@/lib/redis", async () => {
  const actual = await vi.importActual<typeof import("@/lib/redis")>("@/lib/redis");
  return {
    ...actual,
    getRedis: vi.fn(() => new RawStringRedisMock(redis.store)),
  };
});

vi.mock("next/headers", () => ({
  cookies: vi.fn(() => Promise.resolve(new Map())),
}));

// Import after mocks are registered
import { GET as getPopularRoutes } from "../popular-routes/route";

describe("/api/flights/popular-routes", () => {
  beforeEach(() => {
    stubRateLimitDisabled();
    vi.stubEnv("UPSTASH_REDIS_REST_URL", "https://example.com");
    vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "test-token");
    setRateLimitFactoryForTests(async () => ({
      limit: 60,
      remaining: 59,
      reset: Date.now() + 60_000,
      success: true,
    }));
    redis.__reset();
    ratelimit.__reset();
    setSupabaseFactoryForTests(async () => createMockSupabaseClient({ user: null }));
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    redis.__reset();
    ratelimit.__reset();
    setSupabaseFactoryForTests(null);
    vi.unstubAllEnvs();
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
    const body = (await res.json()) as Array<{
      date: string;
      destination: string;
      origin: string;
      price: number;
    }>;

    expect(res.status).toBe(200);

    // Verify response is an array with sufficient fallback routes
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBeGreaterThanOrEqual(3);

    // Verify each item has the expected shape
    for (const route of body) {
      expect(typeof route.origin).toBe("string");
      expect(typeof route.destination).toBe("string");
      expect(typeof route.date).toBe("string");
      expect(typeof route.price).toBe("number");
      expect(route.origin.length).toBeGreaterThan(0);
      expect(route.destination.length).toBeGreaterThan(0);
    }

    // Verify known fallback origins are present
    const origins = body.map((r) => r.origin);
    expect(origins).toContain("New York");
    expect(origins).toContain("Los Angeles");

    // Verify known fallback destinations are present
    const destinations = body.map((r) => r.destination);
    expect(destinations).toContain("London");
    expect(destinations).toContain("Tokyo");
  });
});
