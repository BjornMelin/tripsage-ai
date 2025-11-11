/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  resetAndImport,
  stubRateLimitDisabled,
  stubRateLimitEnabled,
  unstubAllEnvs,
} from "@/test/env-helpers";

const MOCK_INSERT = vi.hoisted(() => vi.fn());
const MOCK_DELETE = vi.hoisted(() => vi.fn());
const LIMIT_SPY = vi.hoisted(() => vi.fn());
const MOCK_SUPABASE = vi.hoisted(() => ({
  auth: {
    getUser: vi.fn(),
  },
}));
const CREATE_SUPABASE = vi.hoisted(() => vi.fn(async () => MOCK_SUPABASE));

vi.mock("@/lib/supabase/rpc", () => ({
  deleteUserApiKey: MOCK_DELETE,
  insertUserApiKey: MOCK_INSERT,
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE,
}));

vi.mock("@upstash/redis", () => ({
  Redis: { fromEnv: vi.fn(() => ({})) },
}));

vi.mock("@upstash/ratelimit", () => {
  const slidingWindow = vi.fn(() => ({}));
  const ctor = vi.fn(function RatelimitMock() {
    return { limit: LIMIT_SPY };
  }) as unknown as {
    new (...args: unknown[]): { limit: ReturnType<typeof LIMIT_SPY> };
    slidingWindow: (...args: unknown[]) => unknown;
  };
  // Provide static like API expected by implementation
  ctor.slidingWindow = slidingWindow as unknown as (...args: unknown[]) => unknown;
  return {
    Ratelimit: ctor,
    slidingWindow,
  };
});

describe("/api/keys routes", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    unstubAllEnvs();
    stubRateLimitDisabled();
    CREATE_SUPABASE.mockReset();
    CREATE_SUPABASE.mockResolvedValue(MOCK_SUPABASE);
    LIMIT_SPY.mockReset();
    MOCK_SUPABASE.auth.getUser.mockReset();
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "test-user" } },
      error: null,
    });
    MOCK_DELETE.mockReset();
    MOCK_INSERT.mockReset();
  });

  it("POST /api/keys returns 400 on invalid body", async () => {
    const { POST } = await resetAndImport<typeof import("../route")>("../route");
    const req = {
      headers: new Headers(),
      json: async () => ({}),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("DELETE /api/keys/[service] deletes key via RPC and returns 204", async () => {
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "u1" } },
      error: null,
    });
    MOCK_DELETE.mockResolvedValue(undefined);
    const route =
      await resetAndImport<typeof import("../[service]/route")>("../[service]/route");
    const req = { headers: new Headers() } as unknown as NextRequest;
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });
    expect(res.status).toBe(204);
    expect(MOCK_DELETE).toHaveBeenCalledWith("u1", "openai");
  });

  it("POST /api/keys throttles per user id and returns headers", async () => {
    stubRateLimitEnabled();
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-123" } },
      error: null,
    });
    LIMIT_SPY.mockResolvedValueOnce({
      limit: 10,
      remaining: 0,
      reset: 123,
      success: false,
    });
    const { POST } = await resetAndImport<typeof import("../route")>("../route");
    const req = {
      headers: new Headers(),
      json: vi.fn(),
    } as unknown as NextRequest;

    const res = await POST(req);

    expect(LIMIT_SPY).toHaveBeenCalledWith("user-123");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("0");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("123");
    expect(req.json).not.toHaveBeenCalled();
  });

  it("DELETE /api/keys/[service] throttles per user id and returns headers", async () => {
    stubRateLimitEnabled();
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-999" } },
      error: null,
    });
    LIMIT_SPY.mockResolvedValueOnce({
      limit: 10,
      remaining: 9,
      reset: 456,
      success: false,
    });
    const route =
      await resetAndImport<typeof import("../[service]/route")>("../[service]/route");
    const req = { headers: new Headers() } as unknown as NextRequest;

    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    });

    expect(LIMIT_SPY).toHaveBeenCalledWith("user-999");
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("10");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("9");
    expect(res.headers.get("X-RateLimit-Reset")).toBe("456");
    expect(MOCK_DELETE).not.toHaveBeenCalled();
  });
});
