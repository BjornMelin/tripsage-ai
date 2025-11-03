/**
 * @fileoverview Unit tests for BYOK GET /api/keys route handler.
 */
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const MOCK_CREATE_SERVER_SUPABASE = vi.hoisted(() => vi.fn());
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: MOCK_CREATE_SERVER_SUPABASE,
}));

describe("GET /api/keys route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("returns key metadata for authenticated user", async () => {
    const order = vi.fn().mockResolvedValue({
      data: [
        {
          created_at: "2025-11-01T00:00:00Z",
          last_used_at: null,
          service_name: "openai",
        },
      ],
      error: null,
    });
    const eq = vi.fn().mockReturnValue({ order });
    const select = vi.fn().mockReturnValue({ eq });
    const from = vi.fn().mockReturnValue({ select });
    MOCK_CREATE_SERVER_SUPABASE.mockResolvedValue({
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      from,
    } as unknown as TypedServerSupabase);
    const { GET } = await import("../route");
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body[0]).toMatchObject({ has_key: true, is_valid: true, service: "openai" });
  });

  it("returns 401 when not authenticated", async () => {
    MOCK_CREATE_SERVER_SUPABASE.mockResolvedValue({
      auth: { getUser: vi.fn(async () => ({ data: { user: null } })) },
    } as unknown as TypedServerSupabase);
    const { GET } = await import("../route");
    const res = await GET();
    expect(res.status).toBe(401);
  });
});
