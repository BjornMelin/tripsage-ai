/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { InsertTables, Tables, UpdateTables } from "@/lib/supabase/database.types";
import type { TypedClient } from "@/lib/supabase/typed-helpers";
import {
  deleteSingle,
  getMaybeSingle,
  getSingle,
  insertSingle,
  updateSingle,
  upsertSingle,
} from "@/lib/supabase/typed-helpers";

/**
 * Create a chained mock object simulating a Supabase table query builder.
 *
 * @param _table Unused table name for parity with production signatures.
 * @returns A fluent mock with insert/update/select/single/eq methods.
 */
type MockChain = {
  delete: ReturnType<typeof vi.fn>;
  eq: (column: string, value: unknown) => MockChain;
  insert: (values: unknown) => MockChain;
  maybeSingle: ReturnType<typeof vi.fn>;
  select: () => MockChain;
  single: ReturnType<typeof vi.fn>;
  update: (values: unknown) => MockChain;
  upsert: (values: unknown, options: unknown) => MockChain;
};

function makeMockFrom(_table: string): MockChain {
  const chain: MockChain = {
    delete: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    insert: vi.fn().mockReturnThis(),
    maybeSingle: vi.fn(),
    select: vi.fn().mockReturnThis(),
    single: vi.fn(),
    update: vi.fn().mockReturnThis(),
    upsert: vi.fn().mockReturnThis(),
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

const userId = "123e4567-e89b-12d3-a456-426614174000";

function mockTripsRow(overrides?: Partial<Tables<"trips">>): Tables<"trips"> {
  return {
    budget: 1000,
    created_at: "2025-01-01T00:00:00Z",
    currency: "USD",
    destination: "NYC",
    end_date: "2025-01-10T00:00:00Z",
    flexibility: {},
    id: 1,
    name: "Test Trip",
    notes: null,
    search_metadata: {},
    start_date: "2025-01-01T00:00:00Z",
    status: "planning",
    travelers: 1,
    trip_type: "leisure",
    updated_at: "2025-01-01T00:00:00Z",
    user_id: userId,
    ...overrides,
  };
}

describe("typed-helpers", () => {
  describe("insertSingle", () => {
    it("returns the inserted row for trips", async () => {
      const client = makeClient();
      const payload: InsertTables<"trips"> = {
        budget: 1000,
        destination: "NYC",
        end_date: "2025-01-10T00:00:00Z",
        name: "Test Trip",
        start_date: "2025-01-01T00:00:00Z",
        travelers: 1,
        user_id: userId,
      };

      const row = mockTripsRow();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({ data: row, error: null });

      const { data, error } = await insertSingle(client, "trips", payload);
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.name).toBe("Test Trip");
    });

    it("returns error when insert fails", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({
        data: null,
        error: { message: "Insert failed" },
      });

      const { data, error } = await insertSingle(client, "trips", {
        budget: 100,
        destination: "LAX",
        end_date: "2025-02-01T00:00:00Z",
        name: "Fail Trip",
        start_date: "2025-01-01T00:00:00Z",
        travelers: 1,
        user_id: userId,
      });
      expect(data).toBeNull();
      expect(error).toBeTruthy();
    });
  });

  describe("updateSingle", () => {
    it("applies filters and returns the updated row", async () => {
      const client = makeClient();
      const updates: Partial<UpdateTables<"trips">> = { name: "Updated" };
      const row = mockTripsRow({ id: 2, name: "Updated" });

      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({ data: row, error: null });

      const result = await updateSingle(client, "trips", updates, (qb) => {
        const chain = qb as unknown as MockChain;
        return chain.eq("id", 2);
      });
      expect(result.error).toBeNull();
      expect(result.data?.id).toBe(2);
      expect(result.data?.name).toBe("Updated");
    });

    it("returns error when update fails", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({
        data: null,
        error: { message: "Update failed" },
      });

      const result = await updateSingle(client, "trips", { name: "Fail" }, (qb) => qb);
      expect(result.data).toBeNull();
      expect(result.error).toBeTruthy();
    });
  });

  describe("getSingle", () => {
    it("returns the fetched row for trips", async () => {
      const client = makeClient();
      const row = mockTripsRow();

      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({ data: row, error: null });

      const { data, error } = await getSingle(client, "trips", (qb) => {
        const chain = qb as unknown as MockChain;
        return chain.eq("id", 1);
      });
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.id).toBe(1);
    });

    it("returns error when row not found", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({
        data: null,
        error: { code: "PGRST116", message: "Not found" },
      });

      const { data, error } = await getSingle(client, "trips", (qb) => qb);
      expect(data).toBeNull();
      expect(error).toBeTruthy();
    });
  });

  describe("deleteSingle", () => {
    it("deletes successfully", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      // Mock delete to return a thenable that resolves
      const deleteChain = {
        eq: vi.fn().mockReturnValue(Promise.resolve({ error: null })),
      };
      (chain.delete as ReturnType<typeof vi.fn>).mockReturnValue(deleteChain);

      const { error } = await deleteSingle(client, "trips", (qb) => {
        return (qb as unknown as typeof deleteChain).eq("id", 1);
      });
      expect(error).toBeNull();
    });

    it("returns error when delete fails", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      const deleteError = { message: "Delete failed" };
      const deleteChain = {
        eq: vi.fn().mockReturnValue(Promise.resolve({ error: deleteError })),
      };
      (chain.delete as ReturnType<typeof vi.fn>).mockReturnValue(deleteChain);

      const { error } = await deleteSingle(client, "trips", (qb) => {
        return (qb as unknown as typeof deleteChain).eq("id", 999);
      });
      expect(error).toBeTruthy();
    });
  });

  describe("getMaybeSingle", () => {
    it("returns the fetched row when found", async () => {
      const client = makeClient();
      const row = mockTripsRow();

      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.maybeSingle.mockResolvedValue({ data: row, error: null });

      const { data, error } = await getMaybeSingle(client, "trips", (qb) => {
        const chain = qb as unknown as MockChain;
        return chain.eq("id", 1);
      });
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.id).toBe(1);
    });

    it("returns null when row not found (no error)", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.maybeSingle.mockResolvedValue({ data: null, error: null });

      const { data, error } = await getMaybeSingle(client, "trips", (qb) => qb);
      expect(data).toBeNull();
      expect(error).toBeNull();
    });

    it("returns error when query fails", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.maybeSingle.mockResolvedValue({
        data: null,
        error: { message: "Query failed" },
      });

      const { data, error } = await getMaybeSingle(client, "trips", (qb) => qb);
      expect(data).toBeNull();
      expect(error).toBeTruthy();
    });
  });

  describe("upsertSingle", () => {
    it("returns the upserted row for trips", async () => {
      const client = makeClient();
      const payload: InsertTables<"trips"> = {
        budget: 1500,
        destination: "LAX",
        end_date: "2025-03-15T00:00:00Z",
        name: "Upsert Trip",
        start_date: "2025-03-01T00:00:00Z",
        travelers: 2,
        user_id: userId,
      };
      const row = mockTripsRow({ ...payload, id: 5 });

      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({ data: row, error: null });

      const { data, error } = await upsertSingle(client, "trips", payload, "user_id");
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.name).toBe("Upsert Trip");
      expect(data?.budget).toBe(1500);
    });

    it("returns error when upsert fails", async () => {
      const client = makeClient();
      const chain = (client as unknown as { from: (table: string) => MockChain }).from(
        "trips"
      );
      chain.single.mockResolvedValue({
        data: null,
        error: { message: "Upsert failed" },
      });

      const { data, error } = await upsertSingle(
        client,
        "trips",
        {
          budget: 100,
          destination: "SFO",
          end_date: "2025-04-01T00:00:00Z",
          name: "Fail Upsert",
          start_date: "2025-03-01T00:00:00Z",
          travelers: 1,
          user_id: userId,
        },
        "user_id"
      );
      expect(data).toBeNull();
      expect(error).toBeTruthy();
    });
  });
});
