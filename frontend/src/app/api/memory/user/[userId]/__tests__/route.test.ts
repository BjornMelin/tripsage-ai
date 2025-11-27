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
} from "@/test/route-helpers";

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

vi.mock("@upstash/redis", async () => {
  const { createRedisMock } = await import("@/test/upstash");
  return createRedisMock();
});

vi.mock("@upstash/ratelimit", async () => {
  const { createRatelimitMock } = await import("@/test/upstash");
  return createRatelimitMock();
});

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

describe("POST /api/memory/user/[userId] (delete memories)", () => {
  beforeEach(async () => {
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

    const redisModule = (await import("@upstash/redis")) as {
      __reset?: () => void;
    };
    const ratelimitModule = (await import("@upstash/ratelimit")) as {
      __reset?: () => void;
    };
    redisModule.__reset?.();
    ratelimitModule.__reset?.();
  });

  afterAll(() => {
    setSupabaseFactoryForTests(null);
    setRateLimitFactoryForTests(null);
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

    const res = await post(req, createRouteParamsContext({ userId: "user-123" }));
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

    const res = await post(req, createRouteParamsContext({ userId: "user-123" }));
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

    const res = await post(req, createRouteParamsContext({}));
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

    const res = await post(req, createRouteParamsContext({ userId: "other-user-id" }));
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

    const res = await post(req, createRouteParamsContext({ userId: "user-123" }));
    const body = (await res.json()) as { deleted: boolean };

    expect(res.status).toBe(200);
    expect(body.deleted).toBe(true);

    // Verify both schema calls were made
    expect(mockSchema).toHaveBeenCalledWith("memories");
    expect(mockFrom).toHaveBeenCalledWith("turns");
    expect(mockFrom).toHaveBeenCalledWith("sessions");

    // Verify delete was called with correct user_id
    expect(mockDelete).toHaveBeenCalled();
    expect(mockEq).toHaveBeenCalledWith("user_id", "user-123");
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

    const res = await post(req, createRouteParamsContext({ userId: "user-123" }));
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

    const res = await post(req, createRouteParamsContext({ userId: "user-123" }));
    const body = (await res.json()) as { error: string };

    expect(res.status).toBe(500);
    expect(body.error).toBe("memory_delete_failed");
  });
});
