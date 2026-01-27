/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import { stubRateLimitDisabled } from "@/test/helpers/env";
import { TEST_USER_ID } from "@/test/helpers/ids";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";

const redisStore = new Map<string, string>();
const redisClient = {
  del: vi.fn((...keys: string[]) => {
    let deleted = 0;
    keys.forEach((key) => {
      if (redisStore.delete(key)) deleted += 1;
    });
    return deleted;
  }),
  get: vi.fn(async (key: string) => redisStore.get(key) ?? null),
  set: vi.fn((key: string, value: string) => {
    redisStore.set(key, value);
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
import { GET as getPopularDestinations } from "../popular-destinations/route";

describe("/api/flights/popular-destinations", () => {
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
    setRateLimitFactoryForTests(async () => ({
      limit: 60,
      remaining: 59,
      reset: Date.now() + 60_000,
      success: true,
    }));
    redisStore.clear();
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
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
    vi.clearAllMocks();
  });

  it("returns cached destinations when present", async () => {
    await redisClient.set(
      "popular-destinations:global",
      JSON.stringify([{ code: "NYC", name: "New York" }])
    );

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/flights/popular-destinations",
    });

    const res = await getPopularDestinations(req, createRouteParamsContext());
    const body = (await res.json()) as unknown;

    expect(res.status).toBe(200);
    expect(body).toEqual([{ code: "NYC", name: "New York" }]);
    expect(supabaseClient.from).not.toHaveBeenCalled();
  });

  it("returns personalized destinations and caches them", async () => {
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: { id: TEST_USER_ID } },
      error: null,
    });

    type DestinationQueryBuilder = {
      select: ReturnType<typeof vi.fn>;
      eq: ReturnType<typeof vi.fn>;
      order: ReturnType<typeof vi.fn>;
      limit: ReturnType<typeof vi.fn>;
      range: ReturnType<typeof vi.fn>;
    };

    const createDestinationQueryBuilder = (result: {
      data: Array<{ destination: string | null }> | null;
      error: Error | null;
    }): DestinationQueryBuilder &
      Promise<{ data: unknown; error: unknown; count: null }> => {
      const builderRef: DestinationQueryBuilder = {
        eq: vi.fn().mockReturnThis(),
        limit: vi.fn().mockReturnThis(),
        order: vi.fn().mockReturnThis(),
        range: vi.fn().mockReturnThis(),
        select: vi.fn().mockReturnThis(),
      };

      const promise = Promise.resolve({
        count: null,
        data: result.data,
        error: result.error,
      });

      return Object.assign(promise, builderRef);
    };

    const builder = createDestinationQueryBuilder({
      data: [{ destination: "LAX" }],
      error: null,
    });

    supabaseClient.from.mockReturnValue(builder);

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/flights/popular-destinations",
    });

    const res = await getPopularDestinations(req, createRouteParamsContext());
    const body = (await res.json()) as Array<{ code: string; name: string }>;

    expect(res.status).toBe(200);
    expect(body).toEqual([{ code: "LAX", name: "LAX" }]);

    const cached = await redisClient.get(`popular-destinations:user:${TEST_USER_ID}`);
    const parsed = cached
      ? (JSON.parse(cached) as Array<{ code: string; name: string }>)
      : null;

    expect(parsed).toEqual([{ code: "LAX", name: "LAX" }]);
  });

  it("falls back to global destinations when cache is empty and user missing", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/flights/popular-destinations",
    });

    const res = await getPopularDestinations(req, createRouteParamsContext());
    const body = (await res.json()) as Array<{ code: string }>;

    expect(res.status).toBe(200);
    expect(body.some((dest) => dest.code === "NYC")).toBe(true);
  });
});
