import { TTL_DRAFT_SECONDS, TTL_FINAL_SECONDS } from "@ai/tools/server/constants";
import { createTravelPlan, saveTravelPlan } from "@ai/tools/server/planning";
import { planSchema } from "@ai/tools/server/planning.schema";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getMockCookiesForTest } from "@/test/route-helpers";

vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: class {
    limit = vi.fn(async () => ({
      limit: 10,
      remaining: 9,
      reset: Math.floor(Date.now() / 1000) + 60,
      success: true,
    }));

    static slidingWindow(limit: number, window: string) {
      return { limit, window } as const;
    }
  },
}));

// Mock next/headers cookies() before any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

type RedisMock = {
  data: Map<string, unknown>;
  ttl: Map<string, number>;
  get: (key: string) => Promise<unknown | null>;
  set: (key: string, value: unknown) => Promise<void>;
  expire: (key: string, seconds: number) => Promise<void>;
  incr: (key: string) => Promise<number>;
  del: (key: string) => Promise<number>;
};

vi.mock("@/lib/redis", () => {
  const data = new Map<string, unknown>();
  const ttl = new Map<string, number>();
  const store: RedisMock = {
    data,
    del: (key) => {
      const existed = data.delete(key);
      ttl.delete(key);
      return Promise.resolve(existed ? 1 : 0);
    },
    expire: (key, seconds) => {
      ttl.set(key, seconds);
      return Promise.resolve();
    },
    get: (key) => Promise.resolve(data.has(key) ? data.get(key) : null),
    incr: (key) => {
      const current = (data.get(key) as number | undefined) ?? 0;
      const next = current + 1;
      data.set(key, next);
      return Promise.resolve(next);
    },
    set: (key, value) => {
      data.set(key, value);
      return Promise.resolve();
    },
    ttl,
  };
  return { getRedis: () => store };
});

let currentUserId = "u1";
const mockCreateServerSupabase = vi.hoisted(() =>
  vi.fn(async () => ({
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
  }))
);

const setUserIdForTests = vi.hoisted(() => (id: string) => {
  currentUserId = id;
});

vi.mock("@/lib/supabase/server", () => ({
  // biome-ignore lint/style/useNamingConvention: test-only helper
  __setUserIdForTests: setUserIdForTests,
  createServerSupabase: mockCreateServerSupabase,
}));

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
    expect(redis.ttl.get(key)).toBe(TTL_DRAFT_SECONDS);
    const plan = redis.data.get(key) as Record<string, unknown>;
    expect(plan.title).toBe("Paris Spring");
    expect(plan.destinations).toEqual(["Paris"]);
    // Schema round-trip
    const parsed = planSchema.safeParse(plan);
    expect(parsed.success).toBe(true);
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
    const ok = await exec<{ success: boolean }>(saveTravelPlan, {
      finalize: true,
      planId: created.planId,
      userId: "u1",
    });
    expect(ok.success).toBe(true);
    const mod = (await import("@/lib/redis")) as unknown as {
      getRedis: () => RedisMock;
    };
    const redis2 = mod.getRedis();
    const key = `travel_plan:${created.planId}`;
    expect(redis2.ttl.get(key)).toBe(TTL_FINAL_SECONDS);
  });
});
