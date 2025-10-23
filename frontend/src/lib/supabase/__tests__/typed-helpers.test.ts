/**
 * @fileoverview Unit smoke tests for typed Supabase helpers.
 */
import { describe, expect, it, vi } from "vitest";
import type { InsertTables, Tables, UpdateTables } from "@/lib/supabase/database.types";
import type { TypedClient } from "@/lib/supabase/typed-helpers";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";

function makeMockFrom<T extends keyof Tables<any>>(_table: T) {
  const chain: any = {
    insert: vi.fn().mockReturnThis(),
    update: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
    single: vi.fn(),
    eq: vi.fn().mockReturnThis(),
  };
  return chain;
}

function makeClient(): TypedClient {
  const chain = makeMockFrom("trips");
  return {
    // Narrow mock type to satisfy compiler while retaining runtime shape
    from(_table: string): unknown {
      return chain;
    },
  } as unknown as TypedClient;
}

describe("typed-helpers", () => {
  it("insertSingle returns the inserted row for trips", async () => {
    const client = makeClient();
    const payload: InsertTables<"trips"> = {
      user_id: "u1",
      name: "Test Trip",
      start_date: "2025-01-01",
      end_date: "2025-01-10",
      destination: "NYC",
      budget: 1000,
      travelers: 1,
    };

    // Wire single() to resolve a basic trips row
    const row: Tables<"trips"> = {
      id: 1,
      user_id: payload.user_id,
      name: payload.name,
      start_date: payload.start_date,
      end_date: payload.end_date,
      destination: payload.destination,
      budget: payload.budget,
      travelers: payload.travelers,
      status: "planning",
      trip_type: "leisure",
      flexibility: {},
      notes: null,
      search_metadata: {},
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    };

    const chain = (client as any).from("trips");
    chain.single.mockResolvedValue({ data: row, error: null });

    const { data, error } = await insertSingle(client, "trips", payload);
    expect(error).toBeNull();
    expect(data).toBeTruthy();
    expect(data!.name).toBe("Test Trip");
  });

  it("updateSingle applies filters and returns the updated row", async () => {
    const client = makeClient();
    const updates: Partial<UpdateTables<"trips">> = { name: "Updated" };
    const row: Tables<"trips"> = {
      id: 2,
      user_id: "u2",
      name: "Updated",
      start_date: "2025-02-01",
      end_date: "2025-02-05",
      destination: "SFO",
      budget: 500,
      travelers: 2,
      status: "planning",
      trip_type: "leisure",
      flexibility: {},
      notes: null,
      search_metadata: {},
      created_at: "2025-02-01T00:00:00Z",
      updated_at: "2025-02-02T00:00:00Z",
    };
    const chain = (client as any).from("trips");
    chain.single.mockResolvedValue({ data: row, error: null });

    const result = await updateSingle(client, "trips", updates, (qb) =>
      // emulate qb.eq(...) chaining in test
      (qb as any).eq("id", 2)
    );
    expect(result.error).toBeNull();
    expect(result.data?.id).toBe(2);
    expect(result.data?.name).toBe("Updated");
  });
});
