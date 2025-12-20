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
  schema: vi.fn(),
};

const mockFrom = vi.fn();
const mockDelete = vi.fn();
const mockEq = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => supabaseClient),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: vi.fn(() => ({
    schema: mockSchema,
  })),
}));

const mockSchema = vi.fn((_schemaName: string) => ({
  from: mockFrom,
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
      data: { user: { id: "user-123" } },
      error: null,
    });

    mockSchema.mockReturnValue({
      from: mockFrom,
    });

    mockFrom.mockReturnValue({
      delete: mockDelete,
    });

    mockDelete.mockReturnValue({
      eq: mockEq,
    });

    mockEq.mockResolvedValue({ error: null });
  });

  afterAll(() => {
    setSupabaseFactoryForTests(null);
    setRateLimitFactoryForTests(null);
    upstashAfterAllHook();
  });

  it("returns 401 when user is unauthenticated", async () => {
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: null,
    });

    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/memory/user/user-123",
    });

    const res = await post(
      req,
      createRouteParamsContext({ intent: "user", userId: "user-123" })
    );
    expect(res.status).toBe(401);
  });

  it("returns 401 when auth returns an error", async () => {
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: null },
      error: { message: "auth failed" },
    });

    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/memory/user/user-123",
    });

    const res = await post(
      req,
      createRouteParamsContext({ intent: "user", userId: "user-123" })
    );
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(401);
    expect(body.error).toBe("unauthorized");
  });

  it("returns 400 when userId parameter is missing", async () => {
    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/memory/user/",
    });

    const res = await post(req, createRouteParamsContext({ intent: "user" }));
    const body = (await res.json()) as { error: string; reason: string };

    expect(res.status).toBe(400);
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toContain("userId must be a non-empty string");
  });

  it("returns 403 when userId in URL does not match authenticated user", async () => {
    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/memory/user/other-user-id",
    });

    const res = await post(
      req,
      createRouteParamsContext({ intent: "user", userId: "other-user-id" })
    );
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(403);
    expect(body.error).toBe("forbidden");
  });

  it("successfully deletes all memories when userId matches authenticated user", async () => {
    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/memory/user/user-123",
    });

    const res = await post(
      req,
      createRouteParamsContext({ intent: "user", userId: "user-123" })
    );
    const body = (await res.json()) as {
      deletedCount: number;
      metadata: { deletionTime: string; userId: string };
      success: boolean;
    };

    expect(res.status).toBe(200);
    expect(body.success).toBe(true);
    expect(body.metadata.userId).toBe("user-123");

    // Verify both schema calls were made
    expect(mockSchema).toHaveBeenCalledWith("memories");
    expect(mockFrom).toHaveBeenCalledWith("turns");
    expect(mockFrom).toHaveBeenCalledWith("sessions");

    // Verify delete was called with correct user_id
    expect(mockDelete).toHaveBeenCalled();
    expect(mockEq).toHaveBeenCalledWith("user_id", "user-123");
  });

  it("supports DELETE for deleting all memories", async () => {
    const del = await importDeleteRoute();
    const req = createMockNextRequest({
      method: "DELETE",
      url: "http://localhost/api/memory/user/user-123",
    });

    const res = await del(
      req,
      createRouteParamsContext({ intent: "user", userId: "user-123" })
    );
    const body = (await res.json()) as { success: boolean };

    expect(res.status).toBe(200);
    expect(body.success).toBe(true);
  });

  it("returns 500 when turns deletion fails", async () => {
    mockEq.mockResolvedValueOnce({
      error: { message: "Database error" },
    });

    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/memory/user/user-123",
    });

    const res = await post(
      req,
      createRouteParamsContext({ intent: "user", userId: "user-123" })
    );
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(500);
    expect(body.error).toBe("memory_delete_failed");
  });

  it("returns 500 when sessions deletion fails", async () => {
    mockEq
      .mockResolvedValueOnce({ error: null }) // turns delete succeeds
      .mockResolvedValueOnce({
        error: { message: "Database error" },
      }); // sessions delete fails

    const post = await importRoute();
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/memory/user/user-123",
    });

    const res = await post(
      req,
      createRouteParamsContext({ intent: "user", userId: "user-123" })
    );
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(500);
    expect(body.error).toBe("memory_delete_failed");
  });
});
