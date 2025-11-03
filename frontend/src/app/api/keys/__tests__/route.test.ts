/* @vitest-environment node */
/**
 * @fileoverview Unit tests for BYOK CRUD route handlers (POST/DELETE).
 */
import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { stubRateLimitDisabled } from "@/test/env-helpers";

const MOCK_INSERT = vi.hoisted(() => vi.fn());
const MOCK_DELETE = vi.hoisted(() => vi.fn());
vi.mock("@/lib/supabase/rpc", () => ({
  deleteUserApiKey: MOCK_DELETE,
  insertUserApiKey: MOCK_INSERT,
}));

describe("/api/keys routes", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("POST /api/keys returns 400 on invalid body", async () => {
    stubRateLimitDisabled();
    vi.resetModules();
    const { POST } = await import("../route");
    const req = {
      headers: new Headers(),
      json: async () => ({}),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("DELETE /api/keys/[service] deletes key via RPC and returns 204", async () => {
    stubRateLimitDisabled();
    vi.mock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      })),
    }));
    MOCK_DELETE.mockResolvedValue(undefined);
    vi.mock("@/lib/supabase/rpc", () => ({ deleteUserApiKey: MOCK_DELETE }));
    vi.resetModules();
    const route = await import("../[service]/route");
    const req = { headers: new Headers() } as unknown as NextRequest;
    const res = await route.DELETE(req, {
      params: Promise.resolve({ service: "openai" }),
    } as any);
    expect(res.status).toBe(204);
    expect(MOCK_DELETE).toHaveBeenCalledWith("u1", "openai");
  });
});
