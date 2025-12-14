/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setSupabaseFactoryForTests } from "@/lib/api/factory";
import { stubRateLimitDisabled } from "@/test/helpers/env";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";
import { setupUpstashMocks } from "@/test/upstash/redis-mock";

const { redis, ratelimit } = setupUpstashMocks();

const redisClient = {
  del: vi.fn((...keys: string[]) => {
    let deleted = 0;
    keys.forEach((key) => {
      if (redis.store.delete(key)) deleted += 1;
    });
    return deleted;
  }),
  get: vi.fn(async (key: string) => redis.store.get(key)?.value ?? null),
  set: vi.fn((key: string, value: string) => {
    redis.store.set(key, { value });
    return "OK";
  }),
};

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => new Map()),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => redisClient),
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
    redisClient.del.mockClear();
    redisClient.get.mockClear();
    redisClient.set.mockClear();
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
    await redisClient.set(
      "popular-routes:global",
      JSON.stringify([
        { date: "May 1, 2026", destination: "Paris", origin: "NYC", price: 123 },
      ])
    );

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
