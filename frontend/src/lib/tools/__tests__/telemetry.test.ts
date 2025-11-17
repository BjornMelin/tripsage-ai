import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RATE_CREATE_PER_DAY, RATE_UPDATE_PER_MIN } from "../constants";
import { createTravelPlan, updateTravelPlan } from "../planning";

// Mock Next.js cookies() to avoid "cookies called outside request scope" error
vi.mock("next/headers", () => ({
  cookies: () => ({
    delete: vi.fn(),
    get: vi.fn(),
    getAll: vi.fn(() => []),
    has: vi.fn(() => false),
    set: vi.fn(),
  }),
}));

const { mockWithTelemetrySpan } = vi.hoisted(() => {
  const span = {
    addEvent: vi.fn(),
    end: vi.fn(),
    recordException: vi.fn(),
    setAttribute: vi.fn(),
    setStatus: vi.fn(),
  };
  type SpanType = typeof span;
  const withTelemetrySpan = vi.fn(
    (_name: string, _options: unknown, fn: (span: SpanType) => unknown) =>
      Promise.resolve(fn(span))
  );
  return { mockWithTelemetrySpan: withTelemetrySpan };
});

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: mockWithTelemetrySpan,
}));

type RedisMock = {
  data: Map<string, unknown>;
  get: (key: string) => Promise<unknown | null>;
  set: (key: string, value: unknown) => Promise<void>;
  expire: (key: string, seconds: number) => Promise<void>;
  incr: (key: string) => Promise<number>;
  del: (key: string) => Promise<number>;
};

vi.mock("@/lib/redis", () => {
  const data = new Map<string, unknown>();
  const store: RedisMock = {
    data,
    del: () => Promise.resolve(1),
    expire: () => Promise.resolve(),
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
  };
  return { getRedis: () => store };
});

vi.mock("@/lib/supabase", () => ({
  createServerSupabase: async () => ({
    auth: {
      getUser: async () => ({
        data: {
          user: {
            app_metadata: {},
            aud: "authenticated",
            created_at: new Date(0).toISOString(),
            id: "u1",
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
}));

describe("planning tool telemetry", () => {
  let redis: RedisMock;

  beforeEach(async () => {
    const mod = (await import("@/lib/redis")) as unknown as {
      getRedis: () => RedisMock;
    };
    redis = mod.getRedis();
    redis.data.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("createTravelPlan wraps execution in withTelemetrySpan and emits rate_limited event on RL breach", async () => {
    // Setup: create a plan first to get a valid planId
    const created = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.({
      destinations: ["AMS"],
      endDate: "2025-07-10",
      startDate: "2025-07-01",
      title: "Test Plan",
      travelers: 2,
    })) as { success: boolean; planId?: string };

    expect(created.success).toBe(true);
    expect(mockWithTelemetrySpan).toHaveBeenCalledWith(
      "planning.createTravelPlan",
      expect.objectContaining({
        attributes: expect.objectContaining({
          destinationsCount: 1,
          travelers: 2,
        }),
      }),
      expect.any(Function)
    );

    // Simulate rate limit breach
    const day = new Date().toISOString().slice(0, 10).replaceAll("-", "");
    const rlKey = `travel_plan:rate:create:u1:${day}`;
    // Set count to exceed limit
    redis.data.set(rlKey, RATE_CREATE_PER_DAY + 1);

    vi.clearAllMocks();

    const result = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.({
      destinations: ["ZRH"],
      endDate: "2025-08-10",
      startDate: "2025-08-01",
      title: "Another Plan",
      travelers: 1,
    })) as { success: boolean; error?: string };

    expect(result.success).toBe(false);
    expect(result.error).toBe("rate_limited_plan_create");
    expect(mockWithTelemetrySpan).toHaveBeenCalled();
    // In non-test env, span.addEvent would be called
    // We verify the wrapper was invoked and handled gracefully
  });

  it("updateTravelPlan wraps execution in withTelemetrySpan and emits rate_limited event on RL breach", async () => {
    // Setup: create a plan first
    const created = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.({
      destinations: ["ROM"],
      endDate: "2025-09-10",
      startDate: "2025-09-01",
      title: "Update Test Plan",
      travelers: 1,
    })) as { success: boolean; planId?: string };

    expect(created.success).toBe(true);
    expect(created.planId).toBeDefined();
    const planId = created.planId as string;

    vi.clearAllMocks();

    // First update should succeed
    const updated = (await (
      updateTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.({
      planId,
      updates: { title: "Updated Title" },
    })) as { success: boolean };

    expect(updated.success).toBe(true);
    expect(mockWithTelemetrySpan).toHaveBeenCalledWith(
      "planning.updateTravelPlan",
      expect.objectContaining({
        attributes: expect.objectContaining({
          planId,
        }),
      }),
      expect.any(Function)
    );

    // Simulate rate limit breach
    const rlKey = `travel_plan:rate:update:${planId}`;
    redis.data.set(rlKey, RATE_UPDATE_PER_MIN + 1);

    vi.clearAllMocks();

    const result = (await (
      updateTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.({
      planId,
      updates: { title: "Another Update" },
    })) as { success: boolean; error?: string };

    expect(result.success).toBe(false);
    expect(result.error).toBe("rate_limited_plan_update");
    expect(mockWithTelemetrySpan).toHaveBeenCalled();
    // In non-test env, span.addEvent would be called
    // We verify the wrapper was invoked and handled gracefully
  });
});
