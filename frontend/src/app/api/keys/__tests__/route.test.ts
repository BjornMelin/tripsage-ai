/**
 * @fileoverview Unit tests for BYOK CRUD route handlers (POST/DELETE).
 */
import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockInsert = vi.hoisted(() => vi.fn());
const mockDelete = vi.hoisted(() => vi.fn());
vi.mock("@/lib/supabase/rpc", () => ({
  insertUserApiKey: mockInsert,
  deleteUserApiKey: mockDelete,
}));

describe("/api/keys routes", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("POST /api/keys returns 400 on invalid body", async () => {
    const { POST } = await import("../route");
    const req = {
      json: async () => ({}),
      headers: new Headers(),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("DELETE /api/keys/[service] deletes key via RPC and returns 204", async () => {
    vi.mock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      })),
    }));
    mockDelete.mockResolvedValue(undefined);
    vi.mock("@/lib/supabase/rpc", () => ({ deleteUserApiKey: mockDelete }));
    const route = await import("../[service]/route");
    const req = { headers: new Headers() } as unknown as NextRequest;
    const res = await route.DELETE(req, { params: { service: "openai" } });
    expect(res.status).toBe(204);
    expect(mockDelete).toHaveBeenCalledWith("u1", "openai");
  });
});
