/**
 * @fileoverview Unit smoke tests for typed Supabase helpers.
 */
import { describe, expect, it, vi } from "vitest";
import type { InsertTables, Tables, UpdateTables } from "@/lib/supabase/database.types";
import type { TypedClient } from "@/lib/supabase/typed-helpers";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";

/**
 * Create a chained mock object simulating a Supabase table query builder.
 *
 * @param _table Unused table name for parity with production signatures.
 * @returns A fluent mock with insert/update/select/single/eq methods.
 */
function makeMockFrom(_table: string) {
  const chain: any = {
    eq: vi.fn().mockReturnThis(),
    insert: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
    single: vi.fn(),
    update: vi.fn().mockReturnThis(),
  };
  return chain;
}

/**
 * Create a minimal `TypedClient` mock that returns the same chain for any table.
 *
 * @returns A `TypedClient` compatible mock.
 */
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
      budget: 1000,
      destination: "NYC",
      end_date: "2025-01-10",
      name: "Test Trip",
      start_date: "2025-01-01",
      travelers: 1,
      user_id: "u1",
    };

    // Wire single() to resolve a basic trips row
    const row: Tables<"trips"> = {
      budget: payload.budget,
      created_at: "2025-01-01T00:00:00Z",
      destination: payload.destination,
      end_date: payload.end_date,
      flexibility: {},
      id: 1,
      name: payload.name,
      notes: null,
      search_metadata: {},
      start_date: payload.start_date,
      status: "planning",
      travelers: payload.travelers,
      trip_type: "leisure",
      updated_at: "2025-01-01T00:00:00Z",
      user_id: payload.user_id,
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
      budget: 500,
      created_at: "2025-02-01T00:00:00Z",
      destination: "SFO",
      end_date: "2025-02-05",
      flexibility: {},
      id: 2,
      name: "Updated",
      notes: null,
      search_metadata: {},
      start_date: "2025-02-01",
      status: "planning",
      travelers: 2,
      trip_type: "leisure",
      updated_at: "2025-02-02T00:00:00Z",
      user_id: "u2",
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
