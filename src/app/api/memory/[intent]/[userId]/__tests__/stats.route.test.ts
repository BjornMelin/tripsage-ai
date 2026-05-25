/** @vitest-environment node */

import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

const { afterAllHook: upstashAfterAllHook, beforeEachHook: upstashBeforeEachHook } =
  setupUpstashTestEnvironment();

const mockHandleMemoryIntent = vi.hoisted(() => vi.fn());
const mockNowIso = vi.hoisted(() => vi.fn(() => "2026-02-03T04:05:06.000Z"));

vi.mock("@/lib/memory/orchestrator", () => ({
  handleMemoryIntent: mockHandleMemoryIntent,
}));

vi.mock("@/lib/security/random", () => ({
  nowIso: mockNowIso,
  secureUuid: vi.fn(() => "00000000-0000-4000-8000-000000000000"),
}));

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
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

async function importRoute() {
  const mod = await import("../route");
  return mod.GET;
}

describe("/api/memory/stats/[userId] route", () => {
  const userId = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
  let Get: Awaited<ReturnType<typeof importRoute>> | null = null;

  beforeAll(async () => {
    Get = await importRoute();
  }, 15_000);

  beforeEach(() => {
    upstashBeforeEachHook();
    vi.clearAllMocks();
    setRateLimitFactoryForTests(async () => ({
      limit: 10,
      remaining: 9,
      reset: Date.now() + 60_000,
      success: true,
    }));
    setSupabaseFactoryForTests(async () => unsafeCast(supabaseClient));
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: { id: userId } },
      error: null,
    });
    mockHandleMemoryIntent.mockResolvedValue({
      context: [
        { context: "Paris", score: 0.9, source: "supabase" },
        { context: "Budget stay", score: 0.7, source: "supabase" },
      ],
      intent: {
        limit: 100,
        sessionId: "",
        type: "fetchContext",
        userId,
      },
      results: [],
      status: "ok",
    });
  });

  afterAll(() => {
    setSupabaseFactoryForTests(null);
    setRateLimitFactoryForTests(null);
    upstashAfterAllHook();
  });

  it("returns memory stats with a shared timestamp helper value", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: `http://localhost/api/memory/stats/${userId}`,
    });

    if (!Get) throw new Error("route not loaded");
    const res = await Get(req, createRouteParamsContext({ intent: "stats", userId }));
    const body = (await res.json()) as {
      lastUpdated: string;
      memoryTypes: Record<string, number>;
      storageSize: number;
      totalMemories: number;
    };

    expect(res.status).toBe(200);
    expect(body.lastUpdated).toBe("2026-02-03T04:05:06.000Z");
    expect(body.memoryTypes.conversation_context).toBe(2);
    expect(body.storageSize).toBe("Paris".length + "Budget stay".length);
    expect(body.totalMemories).toBe(2);
    expect(mockNowIso).toHaveBeenCalledOnce();
    expect(mockHandleMemoryIntent).toHaveBeenCalledWith({
      limit: 100,
      sessionId: "",
      type: "fetchContext",
      userId,
    });
  });
});
