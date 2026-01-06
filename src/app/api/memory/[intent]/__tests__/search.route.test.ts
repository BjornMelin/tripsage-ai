/** @vitest-environment node */

import type { MemoryContextResponse } from "@schemas/chat";
import type { SearchMemoriesResponse } from "@schemas/memory";
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

const mockHandleMemoryIntent = vi.hoisted(() => vi.fn());
const mockNowIso = vi.hoisted(() => vi.fn(() => "2025-01-01T00:00:00.000Z"));
const mockSecureUuid = vi.hoisted(() =>
  vi.fn(() => "3fa85f64-5717-4562-b3fc-2c963f66afa7")
);
const mockLogger = vi.hoisted(() => ({
  error: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
}));

vi.mock("@/lib/security/random", () => ({
  nowIso: mockNowIso,
  secureUuid: mockSecureUuid,
}));

vi.mock("@/lib/memory/orchestrator", () => ({
  handleMemoryIntent: mockHandleMemoryIntent,
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => mockLogger),
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
    if (key.includes("URL")) return "http://upstash.test";
    if (key.includes("TOKEN")) return "test-token";
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
  return mod.POST;
}

describe("/api/memory/search route", () => {
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

  it("returns schema-compliant search results", async () => {
    const post = await importRoute();

    const context: MemoryContextResponse[] = [
      {
        context: "Trip to Paris cost 1200 with museums",
        score: 0.92,
        source: "supabase",
      },
    ];

    mockHandleMemoryIntent.mockResolvedValueOnce({
      context,
      intent: {
        limit: 10,
        query: "paris",
        sessionId: "",
        type: "fetchContext",
        userId,
      },
      results: [],
      status: "ok",
    });

    const req = createMockNextRequest({
      body: {
        query: "paris",
        userId,
      },
      method: "POST",
      url: "http://localhost/api/memory/search",
    });

    const res = await post(req, createRouteParamsContext({ intent: "search" }));
    expect(res.status).toBe(200);
    const body = (await res.json()) as SearchMemoriesResponse;

    expect(body.success).toBe(true);
    expect(body.totalFound).toBe(1);
    expect(body.searchMetadata.queryProcessed).toBe("paris");
    expect(body.memories[0]?.similarityScore).toBeGreaterThanOrEqual(0);
    expect(body.memories[0]?.relevanceReason).toContain("Matched");
    expect(body.memories[0]?.memory.userId).toBe(userId);
    expect(body.memories[0]?.memory.content).toContain("Paris");

    expect(mockHandleMemoryIntent).toHaveBeenCalledWith({
      limit: 10,
      query: "paris",
      sessionId: "",
      type: "fetchContext",
      userId,
    });
  }, 15_000);

  it("filters by similarityThreshold when provided", async () => {
    const post = await importRoute();

    const context: MemoryContextResponse[] = [
      {
        context: "Trip to Paris cost 1200 with museums",
        score: 0.92,
        source: "supabase",
      },
    ];

    mockHandleMemoryIntent.mockResolvedValueOnce({
      context,
      intent: {
        limit: 10,
        query: "trip",
        sessionId: "",
        similarityThreshold: 0.9,
        type: "fetchContext",
        userId,
      },
      results: [],
      status: "ok",
    });

    const req = createMockNextRequest({
      body: {
        query: "trip",
        similarityThreshold: 0.9,
        userId,
      },
      method: "POST",
      url: "http://localhost/api/memory/search",
    });

    const res = await post(req, createRouteParamsContext({ intent: "search" }));
    const body = (await res.json()) as SearchMemoriesResponse;

    expect(res.status).toBe(200);
    expect(body.totalFound).toBe(1);
    expect(body.memories[0]?.memory.content).toContain("Trip to Paris");

    expect(mockHandleMemoryIntent).toHaveBeenCalledWith({
      limit: 10,
      query: "trip",
      sessionId: "",
      similarityThreshold: 0.9,
      type: "fetchContext",
      userId,
    });
  });

  it("returns 403 when request userId does not match auth user", async () => {
    const post = await importRoute();
    const req = createMockNextRequest({
      body: {
        query: "paris",
        userId: "3fa85f64-5717-4562-b3fc-2c963f66afa8",
      },
      method: "POST",
      url: "http://localhost/api/memory/search",
    });

    const res = await post(req, createRouteParamsContext({ intent: "search" }));
    expect(res.status).toBe(403);
    const body = (await res.json()) as { error: string };
    expect(body.error).toBe("forbidden");
  });
});
