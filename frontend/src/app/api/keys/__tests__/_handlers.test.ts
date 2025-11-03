/**
 * @fileoverview Unit tests for keys handler functions, testing BYOK CRUD operations
 * with mocked Supabase client and authentication scenarios.
 */

import { describe, expect, it, vi } from "vitest";
import { getKeys, postKey } from "../_handlers";

/**
 * Creates a mock Supabase client for testing keys handler functions.
 *
 * @param userId - User ID for authentication mocking, or null for unauthenticated.
 * @param rows - Array of database rows for query result mocking.
 * @returns Mock Supabase client with basic operations.
 */
function makeSupabase(userId: string | null, rows: any[] = []) {
  return {
    auth: {
      getUser: vi.fn(async () => ({ data: { user: userId ? { id: userId } : null } })),
    },
    from: vi.fn(() => ({
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockResolvedValue({ data: rows, error: null }),
      select: vi.fn().mockReturnThis(),
    })),
  } as any;
}

describe("keys _handlers", () => {
  it("postKey returns 400 for invalid body", async () => {
    const supabase = makeSupabase("u1");
    const res = await postKey(
      { insertUserApiKey: vi.fn(), supabase },
      { api_key: undefined, service: undefined }
    );
    expect(res.status).toBe(400);
  });

  it("postKey returns 401 when unauthenticated", async () => {
    const supabase = makeSupabase(null);
    const res = await postKey(
      { insertUserApiKey: vi.fn(), supabase },
      { api_key: "sk", service: "openai" }
    );
    expect(res.status).toBe(401);
  });

  it("postKey returns 204 when valid and authenticated", async () => {
    const supabase = makeSupabase("u2");
    const insert = vi.fn(async () => {});
    const res = await postKey(
      { insertUserApiKey: insert, supabase },
      { api_key: "sk", service: "openai" }
    );
    expect(res.status).toBe(204);
    expect(insert).toHaveBeenCalledWith("u2", "openai", "sk");
  });

  it("getKeys returns 200 for authenticated users", async () => {
    const supabase = makeSupabase("u3", [
      { created_at: "2025-11-01", last_used_at: null, service_name: "openai" },
    ]);
    const res = await getKeys({ supabase });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body[0]).toMatchObject({ has_key: true, service: "openai" });
  });
});
