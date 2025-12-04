/** @vitest-environment node */

import { createTravelPlan, updateTravelPlan } from "@ai/tools/server/planning";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getMockCookiesForTest } from "@/test/helpers/route";

// Mock Next.js cookies() before any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
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

const ratelimitFailNext = vi.hoisted(() => ({ fail: false }));

vi.mock("@upstash/ratelimit", () => {
  return {
    Ratelimit: class {
      static slidingWindow(limit: number, window: string) {
        return { limit, window };
      }
      private count = 0;
      private readonly max: number;
      constructor(opts: {
        limiter: { limit: number };
        prefix?: string;
        redis?: unknown;
      }) {
        this.max = opts.limiter.limit;
      }
      limit() {
        this.count += 1;
        const shouldFail = ratelimitFailNext.fail;
        if (shouldFail) {
          ratelimitFailNext.fail = false;
          return {
            limit: this.max,
            remaining: 0,
            reset: Math.floor(Date.now() / 1000) + 60,
            success: false,
          };
        }
        const success = this.count <= this.max;
        return {
          limit: this.max,
          remaining: Math.max(0, this.max - this.count),
          reset: Math.floor(Date.now() / 1000) + 60,
          success,
        };
      }
    },
  };
});

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

describe("planning tool telemetry", () => {
  let redis: RedisMock;

  beforeEach(async () => {
    const mod = (await import("@/lib/redis")) as unknown as {
      getRedis: () => RedisMock;
    };
    redis = mod.getRedis();
    redis.data.clear();
    redis.ttl.clear();
    // Reset user ID to default
    const supabaseMod = (await import("@/lib/supabase/server")) as unknown as {
      __setUserIdForTests: (id: string) => void;
    };
    supabaseMod.__setUserIdForTests("u1");
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("createTravelPlan wraps execution in withTelemetrySpan and emits rate_limited event on RL breach", async () => {
    const callOptions = { messages: [], toolCallId: "call-1" };
    // Setup: create a plan first to get a valid planId
    const created = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        destinations: ["AMS"],
        endDate: "2025-07-10",
        startDate: "2025-07-01",
        title: "Test Plan",
        travelers: 2,
      },
      callOptions
    )) as { success: boolean; planId?: string };

    expect(created.success).toBe(true);
    expect(mockWithTelemetrySpan).toHaveBeenCalled();
    const callArgs = mockWithTelemetrySpan.mock.calls[0];
    expect(callArgs[0]).toBe("tool.createTravelPlan");
    expect(callArgs[1]).toMatchObject({
      attributes: expect.objectContaining({
        "tool.name": "createTravelPlan",
      }),
    });

    // Simulate rate limit breach
    ratelimitFailNext.fail = true;

    vi.clearAllMocks();

    await expect(
      (
        createTravelPlan as unknown as {
          execute?: (a: unknown, c?: unknown) => Promise<unknown>;
        }
      ).execute?.(
        {
          destinations: ["ZRH"],
          endDate: "2025-08-10",
          startDate: "2025-08-01",
          title: "Another Plan",
          travelers: 1,
        },
        callOptions
      )
    ).rejects.toMatchObject({ code: "tool_rate_limited" });
    expect(mockWithTelemetrySpan).toHaveBeenCalled();
  });

  it("updateTravelPlan wraps execution in withTelemetrySpan and emits rate_limited event on RL breach", async () => {
    const callOptions = { messages: [], toolCallId: "call-2" };
    // Setup: create a plan first
    const created = (await (
      createTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        destinations: ["ROM"],
        endDate: "2025-09-10",
        startDate: "2025-09-01",
        title: "Update Test Plan",
        travelers: 1,
      },
      callOptions
    )) as { success: boolean; planId?: string };

    expect(created.success).toBe(true);
    expect(created.planId).toBeDefined();
    const planId = created.planId as string;

    vi.clearAllMocks();

    // First update should succeed
    const updated = (await (
      updateTravelPlan as unknown as {
        execute?: (a: unknown, c?: unknown) => Promise<unknown>;
      }
    ).execute?.(
      {
        planId,
        updates: { title: "Updated Title" },
      },
      callOptions
    )) as { success: boolean };

    expect(updated.success).toBe(true);
    expect(mockWithTelemetrySpan).toHaveBeenCalled();
    const updateCallArgs = mockWithTelemetrySpan.mock.calls[0];
    expect(updateCallArgs[0]).toBe("tool.updateTravelPlan");
    expect(updateCallArgs[1]).toMatchObject({
      attributes: expect.objectContaining({
        "tool.name": "updateTravelPlan",
      }),
    });

    // Simulate rate limit breach
    ratelimitFailNext.fail = true;

    vi.clearAllMocks();

    await expect(
      (
        updateTravelPlan as unknown as {
          execute?: (a: unknown, c?: unknown) => Promise<unknown>;
        }
      ).execute?.(
        {
          planId,
          updates: { title: "Another Update" },
        },
        callOptions
      )
    ).rejects.toMatchObject({ code: "tool_rate_limited" });
    expect(mockWithTelemetrySpan).toHaveBeenCalled();
  });
});
