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

const mockLogger = vi.hoisted(() => ({
  error: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
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

const mockRpc = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => supabaseClient),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: vi.fn(() => ({
    rpc: mockRpc,
  })),
}));

async function importRoute() {
  const mod = await import("../route");
  return mod.POST;
}

async function importDeleteRoute() {
  const mod = await import("../route");
  return mod.DELETE;
}

describe("/api/memory/user/[userId] (delete memories)", () => {
  const userId = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
  const otherUserId = "3fa85f64-5717-4562-b3fc-2c963f66afa8";

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
    mockRpc.mockResolvedValue({
      data: [{ deleted_sessions: 1, deleted_turns: 2 }],
      error: null,
    });
  });

  afterAll(() => {
    setSupabaseFactoryForTests(null);
    setRateLimitFactoryForTests(null);
    upstashAfterAllHook();
  });

  it("returns 405 when attempting deletion via POST", async () => {
    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: `http://localhost/api/memory/user/${userId}`,
    });

    const res = await post(req, createRouteParamsContext({ intent: "user", userId }));

    expect(res.status).toBe(405);
    const body = (await res.json()) as { error: string };
    expect(body.error).toBe("method_not_allowed");
  });

  it("returns 401 when user is unauthenticated", async () => {
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null,
    });

    const del = await importDeleteRoute();
    const req = createMockNextRequest({
      method: "DELETE",
      url: `http://localhost/api/memory/user/${userId}`,
    });

    const res = await del(req, createRouteParamsContext({ intent: "user", userId }));
    expect(res.status).toBe(401);
  });

  it("returns 401 when auth returns an error", async () => {
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: { message: "auth failed" },
    });

    const del = await importDeleteRoute();
    const req = createMockNextRequest({
      method: "DELETE",
      url: `http://localhost/api/memory/user/${userId}`,
    });

    const res = await del(req, createRouteParamsContext({ intent: "user", userId }));
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(401);
    expect(body.error).toBe("unauthorized");
  });

  it("returns 400 when userId parameter is missing", async () => {
    const del = await importDeleteRoute();
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/memory/user/",
    });

    const res = await del(req, createRouteParamsContext({ intent: "user" }));
    const body = (await res.json()) as { error: string; reason: string };

    expect(res.status).toBe(400);
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toContain("userId must be a non-empty string");
  });

  it("returns 403 when userId in URL does not match authenticated user", async () => {
    const del = await importDeleteRoute();
    const req = createMockNextRequest({
      method: "DELETE",
      url: `http://localhost/api/memory/user/${otherUserId}`,
    });

    const res = await del(
      req,
      createRouteParamsContext({ intent: "user", userId: otherUserId })
    );
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(403);
    expect(body.error).toBe("forbidden");
  });

  it("successfully deletes all memories when userId matches authenticated user", async () => {
    const del = await importDeleteRoute();
    const req = createMockNextRequest({
      method: "DELETE",
      url: `http://localhost/api/memory/user/${userId}`,
    });

    const res = await del(req, createRouteParamsContext({ intent: "user", userId }));
    const body = (await res.json()) as {
      deletedCount: number;
      metadata: { deletionTime: string; userId: string };
      success: boolean;
    };

    expect(res.status).toBe(200);
    expect(body.success).toBe(true);
    expect(body.metadata.userId).toBe(userId);
    expect(body.deletedCount).toBe(3);

    expect(mockRpc).toHaveBeenCalledWith("delete_user_memories", {
      p_user_id: userId,
    });
  });

  it("returns 500 when deletion RPC fails", async () => {
    mockRpc.mockResolvedValueOnce({
      data: null,
      error: { message: "Database error" },
    });

    const del = await importDeleteRoute();
    const req = createMockNextRequest({
      method: "DELETE",
      url: `http://localhost/api/memory/user/${userId}`,
    });

    const res = await del(req, createRouteParamsContext({ intent: "user", userId }));
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(500);
    expect(body.error).toBe("memory_delete_failed");
  });
});
