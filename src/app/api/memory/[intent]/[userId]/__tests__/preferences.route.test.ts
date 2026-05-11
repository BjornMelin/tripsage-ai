/** @vitest-environment node */

import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

const { afterAllHook: upstashAfterAllHook, beforeEachHook: upstashBeforeEachHook } =
  setupUpstashTestEnvironment();

const addConversationMemoryExecute = vi.hoisted(() => vi.fn());
const deleteCachedJsonMock = vi.hoisted(() => vi.fn(async () => undefined));

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

vi.mock("@ai/tools", () => ({
  addConversationMemory: {
    execute: addConversationMemoryExecute,
  },
}));

vi.mock("@/lib/cache/upstash", () => ({
  deleteCachedJson: deleteCachedJsonMock,
  getCachedJson: vi.fn(async () => null),
  setCachedJson: vi.fn(async () => undefined),
}));

vi.mock("@/lib/redis", async () => {
  const { RedisMockClient, sharedUpstashStore } = await import(
    "@/test/upstash/redis-mock"
  );
  const client = new RedisMockClient(sharedUpstashStore);
  return {
    getRedis: () => client,
  };
});

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn((key: string, fallback?: string) => {
    if (key === "UPSTASH_REDIS_REST_URL") return "http://upstash.test";
    if (key === "UPSTASH_REDIS_REST_TOKEN") return "test-token";
    return fallback ?? "";
  }),
}));

const supabaseClient = {
  auth: {
    getUser: vi.fn(),
  },
};

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => supabaseClient),
}));

describe("/api/memory/preferences/[userId] route", () => {
  const userId = "3fa85f64-5717-4562-b3fc-2c963f66afa6";

  beforeEach(() => {
    upstashBeforeEachHook();
    vi.clearAllMocks();
    setRateLimitFactoryForTests(async () => ({
      limit: 10,
      remaining: 9,
      reset: Date.now() + 60_000,
      success: true,
    }));
    setSupabaseFactoryForTests(async () => supabaseClient as never);
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: { id: userId } },
      error: null,
    });
  });

  afterAll(() => {
    setSupabaseFactoryForTests(null);
    setRateLimitFactoryForTests(null);
    upstashAfterAllHook();
  });

  it("returns 207 when preference updates partially succeed", async () => {
    addConversationMemoryExecute
      .mockResolvedValueOnce({
        createdAt: "2026-01-01T00:00:00.000Z",
        id: "memory-travel-style",
      })
      .mockRejectedValueOnce(new Error("memory write failed"));

    const { POST } = await import("../route");
    const req = createMockNextRequest({
      body: {
        preferences: {
          travelStyle: "budget",
          tripPurpose: "museums",
        },
      },
      method: "POST",
      url: `http://localhost:3000/api/memory/preferences/${userId}`,
    });

    const res = await POST(
      req,
      createRouteParamsContext({ intent: "preferences", userId })
    );
    const body = (await res.json()) as {
      failedKeys: string[];
      preferences: Record<string, unknown>;
      updated: number;
    };

    expect(res.status).toBe(207);
    expect(body).toEqual({
      failedKeys: ["tripPurpose"],
      preferences: {
        travelStyle: {
          createdAt: "2026-01-01T00:00:00.000Z",
          id: "memory-travel-style",
        },
        tripPurpose: null,
      },
      updated: 1,
    });
    expect(deleteCachedJsonMock).toHaveBeenCalledWith(`memory:insights:${userId}`, {
      namespace: "memory",
    });
  });
});
