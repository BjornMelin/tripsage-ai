/**
 * @fileoverview Unit tests for BYOK GET /api/keys route handler.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCreateServerSupabase = vi.hoisted(() => vi.fn());
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: mockCreateServerSupabase,
}));

describe("GET /api/keys route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("returns key metadata for authenticated user", async () => {
    const select = vi.fn().mockReturnValue({
      order: vi.fn().mockResolvedValue({
        data: [
          {
            service: "openai",
            created_at: "2025-11-01T00:00:00Z",
            last_used: null,
          },
        ],
        error: null,
      }),
    });
    const from = vi.fn().mockReturnValue({ select });
    mockCreateServerSupabase.mockResolvedValue({
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      from,
    } as any);
    const { GET } = await import("../route");
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body[0]).toMatchObject({ service: "openai", has_key: true, is_valid: true });
  });

  it("returns 401 when not authenticated", async () => {
    mockCreateServerSupabase.mockResolvedValue({
      auth: { getUser: vi.fn(async () => ({ data: { user: null } })) },
    } as any);
    const { GET } = await import("../route");
    const res = await GET();
    expect(res.status).toBe(401);
  });
});
