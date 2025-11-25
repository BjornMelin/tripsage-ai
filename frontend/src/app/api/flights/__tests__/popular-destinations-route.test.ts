/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setSupabaseFactoryForTests } from "@/lib/api/factory";
import { stubRateLimitDisabled } from "@/test/env-helpers";
import { createMockNextRequest, createRouteParamsContext } from "@/test/route-helpers";

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
      data: { user: { id: "user-1" } },
      error: null,
    });

    type DestinationQueryBuilder = {
      select: ReturnType<typeof vi.fn>;
      eq: ReturnType<typeof vi.fn>;
      order: ReturnType<typeof vi.fn>;
      limit: ReturnType<typeof vi.fn>;
      returns: ReturnType<typeof vi.fn>;
    };

    const builder: DestinationQueryBuilder = (() => {
      const returns = vi.fn(async () => ({
        data: [{ count: 3, destination: "LAX" }],
        error: null,
      }));

      const builderRef: DestinationQueryBuilder = {
        eq: vi.fn(() => builderRef),
        limit: vi.fn(() => builderRef),
        order: vi.fn(() => builderRef),
        returns,
        select: vi.fn(() => builderRef),
      };

      return builderRef;
    })();

    supabaseClient.from.mockReturnValue(builder);

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/flights/popular-destinations",
    });

    const res = await getPopularDestinations(req, createRouteParamsContext());
    const body = (await res.json()) as Array<{ code: string; name: string }>;

    expect(res.status).toBe(200);
    expect(body).toEqual([{ code: "LAX", name: "LAX" }]);

    const cached = await redisClient.get("popular-destinations:user:user-1");
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
