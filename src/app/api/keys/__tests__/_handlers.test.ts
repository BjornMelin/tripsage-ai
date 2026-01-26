/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { Tables } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { TEST_USER_ID } from "@/test/helpers/ids";
import { createMockSupabaseClient, getSupabaseMockState } from "@/test/mocks/supabase";
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
  rows: Array<
    Pick<Tables<"api_keys">, "service" | "created_at" | "last_used" | "user_id">
  > = []
) {
  const supabase = createMockSupabaseClient({ user: userId ? { id: userId } : null });
  getSupabaseMockState(supabase).selectResult = {
    count: null,
    data: rows,
    error: null,
  };
  return supabase;
}

describe("keys _handlers", () => {
  it("postKey returns 400 for unsupported service", async () => {
    const supabase = makeSupabase(TEST_USER_ID);
    const res = await postKey(
      { insertUserApiKey: vi.fn(), supabase, userId: TEST_USER_ID },
      { apiKey: "sk-test", service: "invalid-service" }
    );
    expect(res.status).toBe(400);
  });

  it("postKey returns 204 when valid and authenticated", async () => {
    const supabase = makeSupabase(TEST_USER_ID);
    const insert = vi.fn(async () => {
      // Intentional no-op for successful insert mock
    });
    const res = await postKey(
      { insertUserApiKey: insert, supabase, userId: TEST_USER_ID },
      { apiKey: "sk-test", service: "openai" }
    );
    expect(res.status).toBe(204);
    expect(insert).toHaveBeenCalledWith(TEST_USER_ID, "openai", "sk-test");
  });

  it("postKey maps Supabase insert failures to VAULT_UNAVAILABLE", async () => {
    const supabase = makeSupabase(TEST_USER_ID);
    const insert = vi.fn(() => {
      throw new Error("vault unreachable");
    });
    const res = await postKey(
      { insertUserApiKey: insert, supabase, userId: TEST_USER_ID },
      { apiKey: "sk-test", service: "openai" }
    );
    expect(res.status).toBe(500);
    expect(await res.json()).toMatchObject({ error: "VAULT_UNAVAILABLE" });
  });

  it("getKeys returns 200 for authenticated users", async () => {
    const supabase = makeSupabase(TEST_USER_ID, [
      {
        created_at: "2025-11-01",
        last_used: null,
        service: "openai",
        user_id: TEST_USER_ID,
      },
    ]);
    const res = await getKeys({ supabase, userId: TEST_USER_ID });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body[0]).toMatchObject({ hasKey: true, service: "openai" });
  });

  it("getKeys maps query errors to VAULT_UNAVAILABLE", async () => {
    const supabase: TypedServerSupabase = createMockSupabaseClient({
      user: { id: TEST_USER_ID },
    });
    getSupabaseMockState(supabase).selectResult = {
      count: null,
      data: null,
      error: new Error("db down"),
    };

    const res = await getKeys({ supabase, userId: TEST_USER_ID });
    expect(res.status).toBe(500);
    expect(await res.json()).toMatchObject({ error: "VAULT_UNAVAILABLE" });
  });
});
