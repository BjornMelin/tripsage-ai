/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { Tables } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { getKeys, postKey } from "../_handlers";

/**
 * Creates a mock Supabase client for testing keys handler functions.
 *
 * @param userId - User ID for authentication mocking, or null for unauthenticated.
 * @param rows - Array of database rows for query result mocking.
 * @returns Mock Supabase client with basic operations.
 */
function makeSupabase(
  userId: string | null,
  rows: Array<Pick<Tables<"api_keys">, "service" | "created_at" | "last_used">> = []
) {
  return {
    auth: {
      getUser: vi.fn(async () => ({ data: { user: userId ? { id: userId } : null } })),
    },
    from: vi.fn(() => ({
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockResolvedValue({ data: rows, error: null }),
      select: vi.fn().mockReturnThis(),
    })),
  } as unknown as TypedServerSupabase;
}

describe("keys _handlers", () => {
  it("postKey returns 400 for unsupported service", async () => {
    const supabase = makeSupabase("u1");
    const res = await postKey(
      { insertUserApiKey: vi.fn(), supabase, userId: "u1" },
      { apiKey: "sk-test", service: "invalid-service" }
    );
    expect(res.status).toBe(400);
  });

  it("postKey returns 204 when valid and authenticated", async () => {
    const supabase = makeSupabase("u2");
    const insert = vi.fn(async () => {
      // Intentional no-op for successful insert mock
    });
    const res = await postKey(
      { insertUserApiKey: insert, supabase, userId: "u2" },
      { apiKey: "sk-test", service: "openai" }
    );
    expect(res.status).toBe(204);
    expect(insert).toHaveBeenCalledWith("u2", "openai", "sk-test");
  });

  it("postKey maps Supabase insert failures to VAULT_UNAVAILABLE", async () => {
    const supabase = makeSupabase("u2");
    const insert = vi.fn(() => {
      throw new Error("vault unreachable");
    });
    const res = await postKey(
      { insertUserApiKey: insert, supabase, userId: "u2" },
      { apiKey: "sk-test", service: "openai" }
    );
    expect(res.status).toBe(500);
    expect(await res.json()).toMatchObject({ error: "VAULT_UNAVAILABLE" });
  });

  it("getKeys returns 200 for authenticated users", async () => {
    const supabase = makeSupabase("u3", [
      { created_at: "2025-11-01", last_used: null, service: "openai" },
    ]);
    const res = await getKeys({ supabase, userId: "u3" });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body[0]).toMatchObject({ hasKey: true, service: "openai" });
  });

  it("getKeys maps query errors to VAULT_UNAVAILABLE", async () => {
    const order = vi
      .fn()
      .mockResolvedValue({ data: null, error: new Error("db down") });
    const eq = vi.fn().mockReturnValue({ order });
    const select = vi.fn().mockReturnValue({ eq });
    const from = vi.fn().mockReturnValue({ select });
    const supabase = { from } as unknown as TypedServerSupabase;

    const res = await getKeys({ supabase, userId: "u3" });
    expect(res.status).toBe(500);
    expect(await res.json()).toMatchObject({ error: "VAULT_UNAVAILABLE" });
  });
});
