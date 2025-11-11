import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  combineSearchResults,
  createTravelPlan,
  saveTravelPlan,
  updateTravelPlan,
} from "../planning";

type RedisMock = {
  data: Map<string, unknown>;
  ttl: Map<string, number>;
  get: (key: string) => Promise<unknown | null>;
  set: (key: string, value: unknown) => Promise<void>;
  expire: (key: string, seconds: number) => Promise<void>;
};

vi.mock("@/lib/redis", () => {
  const data = new Map<string, unknown>();
  const ttl = new Map<string, number>();
  const store: RedisMock = {
    data,
    expire: (key, seconds) => {
      ttl.set(key, seconds);
      return Promise.resolve();
    },
    get: (key) => Promise.resolve(data.has(key) ? data.get(key) : null),
    set: (key, value) => {
      data.set(key, value);
      return Promise.resolve();
    },
    ttl,
  };
  return { getRedis: () => store };
});

vi.mock("@/lib/supabase/server", () => {
  let currentUserId = "u1";
  return {
    // biome-ignore lint/style/useNamingConvention: test-only helper
    __setUserIdForTests: (id: string) => {
      currentUserId = id;
    },
    createServerSupabase: async () => ({
      auth: {
        getUser: async () => ({
          data: {
            user: {
              app_metadata: {},
              aud: "authenticated",
              created_at: new Date(0).toISOString(),
              id: currentUserId,
              user_metadata: {},
            },
          },
          error: null,
        }),
      },
      from: () => ({
        insert: () => ({
          select: () => ({ single: async () => ({ data: { id: 1 } }) }),
        }),
      }),
    }),
  };
});

describe("planning tools", () => {
  let redis: RedisMock;

  beforeEach(async () => {
    const mod = (await import("@/lib/redis")) as unknown as {
      getRedis: () => RedisMock;
    };
    redis = mod.getRedis();
    redis.data.clear();
    redis.ttl.clear();
  });

  it("finalized plan TTL remains 30d after update", async () => {
    const created = await exec<{ success: boolean; planId: string }>(createTravelPlan, {
      destinations: ["AMS"],
      endDate: "2025-07-10",
      startDate: "2025-07-05",
      title: "TTL Test",
      travelers: 1,
      userId: "u1",
    });
    if (!created?.success) throw new Error("create failed");
    const fin = await exec<{ success: boolean }>(saveTravelPlan, {
      finalize: true,
      planId: created.planId,
      userId: "u1",
    });
    expect(fin.success).toBe(true);
    // update after finalization (session is u1 in our default mock)
    const ok = await exec<{ success: boolean }>(updateTravelPlan, {
      planId: created.planId,
      updates: { title: "Updated TTL" },
      userId: "ignored",
    });
    expect(ok.success).toBe(true);
    const mod = (await import("@/lib/redis")) as unknown as {
      getRedis: () => RedisMock;
    };
    const redis2 = mod.getRedis();
    const key = `travel_plan:${created.planId}`;
    expect(redis2.ttl.get(key)).toBe(86400 * 30);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const exec = async <T>(toolObj: unknown, args: Record<string, unknown>) =>
    (toolObj as { execute?: (a: unknown, c?: unknown) => Promise<T> }).execute?.(
      args,
      {}
    ) as Promise<T>;

  it("createTravelPlan stores plan with 7d TTL and returns id", async () => {
    const res = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        budget: 1500,
        destinations: ["Paris"],
        endDate: "2025-04-14",
        startDate: "2025-04-10",
        title: "Paris Spring",
        travelers: 2,
        userId: "u1",
      },
      {}
    )) as { success: boolean; planId: string };
    expect(res.success).toBe(true);
    const key = `travel_plan:${res.planId}`;
    expect(redis.data.has(key)).toBe(true);
    expect(redis.ttl.get(key)).toBe(86400 * 7);
    const plan = redis.data.get(key) as Record<string, unknown>;
    expect(plan.title).toBe("Paris Spring");
    expect(plan.destinations).toEqual(["Paris"]);
  });

  it("updateTravelPlan rejects unauthorized user and accepts authorized changes", async () => {
    const created = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        destinations: ["Rome"],
        endDate: "2025-05-05",
        startDate: "2025-05-01",
        title: "Trip",
        travelers: 1,
        userId: "u1",
      },
      {}
    )) as { success: boolean; planId: string };
    if (!created?.success) throw new Error("create failed");

    // simulate session user mismatch (unauthorized)
    const supabaseMod = await import("@/lib/supabase/server");
    (
      supabaseMod as unknown as { __setUserIdForTests: (id: string) => void }
    ).__setUserIdForTests("u2");
    const unauth = (await (
      updateTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      { planId: created.planId, updates: { title: "Hack" }, userId: "ignored" },
      {}
    )) as { success: boolean };
    (
      supabaseMod as unknown as { __setUserIdForTests: (id: string) => void }
    ).__setUserIdForTests("u1");
    expect(unauth.success).toBe(false);
    // Authorized update
    const ok = (await (
      updateTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        planId: created.planId,
        updates: { budget: 999, title: "Updated" },
        userId: "u1",
      },
      {}
    )) as { success: boolean };
    expect(ok.success).toBe(true);
    const key = `travel_plan:${created.planId}`;
    const plan = redis.data.get(key) as Record<string, unknown>;
    expect(plan.title).toBe("Updated");
    expect(plan.budget).toBe(999);
  });

  it("combineSearchResults merges lists and computes totals", async () => {
    const res = (await (
      combineSearchResults as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        accommodationResults: {
          accommodations: [
            { price_per_night: 120, rating: 4.5 },
            { price_per_night: 100, rating: 4.0 },
          ],
        },
        activityResults: {
          activities: [
            { price_per_person: 60, rating: 5 },
            { price_per_person: 40, rating: 4.9 },
            { price_per_person: 30, rating: 4.8 },
          ],
        },
        destinationInfo: { highlights: ["Museum", "Park"], tips: ["Metro"] },
        flightResults: { offers: [{ total_amount: 500 }, { total_amount: 750 }] },
      },
      {}
    )) as {
      success: boolean;
      combinedResults: {
        recommendations: { flights: unknown[] };
        totalEstimatedCost: number;
        destinationHighlights: string[];
      };
    };
    expect(res.success).toBe(true);
    const { combinedResults } = res;
    expect(combinedResults.recommendations.flights.length).toBeGreaterThan(0);
    expect(combinedResults.totalEstimatedCost).toBeGreaterThan(0);
    expect(combinedResults.destinationHighlights).toEqual(["Museum", "Park"]);
  });

  it("saveTravelPlan handles missing plan and finalize extends TTL", async () => {
    const missing = (await (
      saveTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      { planId: "5c16b2a9-38ba-4a86-a3a9-5b90d8ef3b8c", userId: "u1" },
      {}
    )) as { success: boolean };
    expect(missing.success).toBe(false);

    const created = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        destinations: ["NYC"],
        endDate: "2025-06-03",
        startDate: "2025-06-01",
        title: "Trip2",
        userId: "u1",
      },
      {}
    )) as { success: boolean; planId: string };
    if (!created?.success) throw new Error("create failed");
    const fin = (await (
      saveTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.({ finalize: true, planId: created.planId, userId: "u1" }, {})) as {
      success: boolean;
    };
    expect(fin.success).toBe(true);
    const key = `travel_plan:${created.planId}`;
    expect(redis.ttl.get(key)).toBe(86400 * 30);
  });

  it("returns redis_unavailable when no Redis client", async () => {
    const spy = vi
      .spyOn(await import("@/lib/redis"), "getRedis")
      .mockReturnValue(undefined as unknown as never);
    const res = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        destinations: ["ZRH"],
        endDate: "2025-01-02",
        startDate: "2025-01-01",
        title: "NoRedis",
        userId: "u1",
      },
      {}
    )) as { success: boolean; error?: string };
    expect(res.success).toBe(false);
    expect(res.error).toBe("redis_unavailable");
    spy.mockRestore();
  });
});
