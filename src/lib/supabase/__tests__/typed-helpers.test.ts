/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { Tables, TablesInsert, TablesUpdate } from "@/lib/supabase/database.types";
import type { TypedClient } from "@/lib/supabase/typed-helpers";
import {
  deleteSingle,
  getMany,
  getMaybeSingle,
  getSingle,
  insertMany,
  insertSingle,
  updateMany,
  updateSingle,
  upsertMany,
  upsertSingle,
} from "@/lib/supabase/typed-helpers";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

/**
 * Create a chained mock object simulating a Supabase table query builder.
 *
 * @returns A fluent mock with insert/update/select/single/eq methods.
 */
type MockChain = {
  delete: ReturnType<typeof vi.fn>;
  eq: (column: string, value: unknown) => MockChain;
  insert: (values: unknown) => MockChain;
  maybeSingle: ReturnType<typeof vi.fn>;
  order: ReturnType<typeof vi.fn>;
  range: ReturnType<typeof vi.fn>;
  select: ReturnType<typeof vi.fn>;
  single: ReturnType<typeof vi.fn>;
  update: (values: unknown) => MockChain;
  upsert: (values: unknown, options: unknown) => MockChain;
};

function makeMockFrom(): MockChain {
  const chain: MockChain = {
    delete: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    insert: vi.fn().mockReturnThis(),
    maybeSingle: vi.fn(),
    order: vi.fn().mockReturnThis(),
    range: vi.fn().mockReturnThis(),
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
 * @returns A `TypedClient` compatible mock plus the underlying chain.
 */
function makeClientWithChain(): { client: TypedClient; chain: MockChain } {
  const chain = makeMockFrom();
  const client = unsafeCast<TypedClient>({
    from(_table: string): unknown {
      return chain;
    },
  });
  return { chain, client };
}

const userId = "123e4567-e89b-12d3-a456-426614174000";

function mockTripsRow(overrides?: Partial<Tables<"trips">>): Tables<"trips"> {
  return {
    budget: 1000,
    created_at: "2025-01-01T00:00:00Z",
    currency: "USD",
    description: null,
    destination: "NYC",
    end_date: "2025-01-10",
    flexibility: {},
    id: 1,
    name: "Test Trip",
    search_metadata: {},
    start_date: "2025-01-01",
    status: "planning",
    tags: [],
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
      const { client, chain } = makeClientWithChain();
      const payload: TablesInsert<"trips"> = {
        budget: 1000,
        destination: "NYC",
        end_date: "2025-01-10",
        name: "Test Trip",
        start_date: "2025-01-01",
        travelers: 1,
        user_id: userId,
      };

      const row = mockTripsRow();
      chain.single.mockResolvedValue({ data: row, error: null });

      const { data, error } = await insertSingle(client, "trips", payload);
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.name).toBe("Test Trip");
    });

    it("supports partial selects when validation is disabled", async () => {
      const { client, chain } = makeClientWithChain();
      const payload: TablesInsert<"trips"> = {
        budget: 1000,
        destination: "NYC",
        end_date: "2025-01-10",
        name: "Test Trip",
        start_date: "2025-01-01",
        travelers: 1,
        user_id: userId,
      };

      chain.single.mockResolvedValue({
        data: unsafeCast<Tables<"trips">>({ id: 1 }),
        error: null,
      });

      const { data, error } = await insertSingle(client, "trips", payload, {
        select: "id",
        validate: false,
      });

      expect(error).toBeNull();
      expect(chain.select).toHaveBeenCalledWith("id");
      expect(data?.id).toBe(1);
    });

    it("returns error when validation is requested with a partial select", async () => {
      const { client, chain } = makeClientWithChain();
      const payload: TablesInsert<"trips"> = {
        budget: 1000,
        destination: "NYC",
        end_date: "2025-01-10",
        name: "Test Trip",
        start_date: "2025-01-01",
        travelers: 1,
        user_id: userId,
      };

      const { data, error } = await insertSingle(client, "trips", payload, {
        select: "id",
        validate: true,
      });

      expect(data).toBeNull();
      expect(error).toBeTruthy();
      expect(chain.insert).not.toHaveBeenCalled();
    });

    it("returns error when insert fails", async () => {
      const { client, chain } = makeClientWithChain();
      chain.single.mockResolvedValue({
        data: null,
        error: { message: "Insert failed" },
      });

      const { data, error } = await insertSingle(client, "trips", {
        budget: 100,
        destination: "LAX",
        end_date: "2025-02-01",
        name: "Fail Trip",
        start_date: "2025-01-01",
        travelers: 1,
        user_id: userId,
      });
      expect(data).toBeNull();
      expect(error).toBeTruthy();
    });
  });

  describe("updateSingle", () => {
    it("applies filters and returns the updated row", async () => {
      const { client, chain } = makeClientWithChain();
      const updates: Partial<TablesUpdate<"trips">> = { name: "Updated" };
      const row = mockTripsRow({ id: 2, name: "Updated" });

      chain.single.mockResolvedValue({ data: row, error: null });

      const result = await updateSingle(client, "trips", updates, (qb) => {
        return qb.eq("id", 2);
      });
      expect(result.error).toBeNull();
      expect(result.data?.id).toBe(2);
      expect(result.data?.name).toBe("Updated");
    });

    it("returns error when update fails", async () => {
      const { client, chain } = makeClientWithChain();
      chain.single.mockResolvedValue({
        data: null,
        error: { message: "Update failed" },
      });

      const result = await updateSingle(client, "trips", { name: "Fail" }, (qb) => qb);
      expect(result.data).toBeNull();
      expect(result.error).toBeTruthy();
    });

    it("returns error when validation is requested with a partial select", async () => {
      const { client, chain } = makeClientWithChain();
      const result = await updateSingle(
        client,
        "trips",
        { name: "Updated" },
        (qb) => qb,
        {
          select: "id",
          validate: true,
        }
      );
      expect(result.data).toBeNull();
      expect(result.error).toBeTruthy();
      expect(chain.update).not.toHaveBeenCalled();
    });
  });

  describe("updateMany", () => {
    it("returns count when update succeeds", async () => {
      const { client, chain } = makeClientWithChain();
      const updates: Partial<TablesUpdate<"trips">> = { status: "completed" };

      const updatePromise = Promise.resolve({ count: 2, error: null });
      (chain.update as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(updatePromise, chain) as MockChain
      );

      const { count, error } = await updateMany(client, "trips", updates, (qb) =>
        qb.eq("status", "planning")
      );
      expect(error).toBeNull();
      expect(count).toBe(2);
    });

    it("omits count preference when count is null", async () => {
      const { client, chain } = makeClientWithChain();
      const updates: Partial<TablesUpdate<"trips">> = { status: "completed" };

      const updatePromise = Promise.resolve({ count: 0, error: null });
      (chain.update as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(updatePromise, chain) as MockChain
      );

      const { count, error } = await updateMany(client, "trips", updates, (qb) => qb, {
        count: null,
      });
      expect(error).toBeNull();
      expect(count).toBe(0);
      expect(chain.update).toHaveBeenCalledWith(updates);
    });

    it("returns error when update fails", async () => {
      const { client, chain } = makeClientWithChain();
      const updates: Partial<TablesUpdate<"trips">> = { status: "cancelled" };

      const updatePromise = Promise.resolve({
        count: 0,
        error: { message: "Update failed" },
      });
      (chain.update as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(updatePromise, chain) as MockChain
      );

      const { count, error } = await updateMany(client, "trips", updates, (qb) => qb);
      expect(count).toBe(0);
      expect(error).toBeTruthy();
    });
  });

  describe("getSingle", () => {
    it("returns the fetched row for trips", async () => {
      const { client, chain } = makeClientWithChain();
      const row = mockTripsRow();

      chain.single.mockResolvedValue({ data: row, error: null });

      const { data, error } = await getSingle(client, "trips", (qb) => qb.eq("id", 1));
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.id).toBe(1);
    });

    it("returns error when row not found", async () => {
      const { client, chain } = makeClientWithChain();
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
      const { client, chain } = makeClientWithChain();
      // Mock delete to return a thenable that resolves
      const deleteResult = Promise.resolve({ count: 1, error: null });
      (chain.delete as ReturnType<typeof vi.fn>).mockReturnValue(deleteResult);

      const { count, error } = await deleteSingle(client, "trips", () => {
        return unsafeCast(deleteResult);
      });
      expect(count).toBe(1);
      expect(error).toBeNull();
    });

    it("omits count preference when count is null", async () => {
      const { client, chain } = makeClientWithChain();
      const deleteResult = Promise.resolve({ count: 0, error: null });
      (chain.delete as ReturnType<typeof vi.fn>).mockReturnValue(deleteResult);

      const { count, error } = await deleteSingle(
        client,
        "trips",
        () => unsafeCast(deleteResult),
        { count: null }
      );
      expect(count).toBe(0);
      expect(error).toBeNull();
      expect(chain.delete).toHaveBeenCalledWith();
    });

    it("returns error when delete fails", async () => {
      const { client, chain } = makeClientWithChain();
      const deleteError = { message: "Delete failed" };
      const deleteResult = Promise.resolve({ count: 0, error: deleteError });
      (chain.delete as ReturnType<typeof vi.fn>).mockReturnValue(deleteResult);

      const { count, error } = await deleteSingle(client, "trips", () => {
        return unsafeCast(deleteResult);
      });
      expect(count).toBe(0);
      expect(error).toBeTruthy();
    });
  });

  describe("getMaybeSingle", () => {
    it("returns the fetched row when found", async () => {
      const { client, chain } = makeClientWithChain();
      const row = mockTripsRow();

      chain.maybeSingle.mockResolvedValue({ data: row, error: null });

      const { data, error } = await getMaybeSingle(client, "trips", (qb) =>
        qb.eq("id", 1)
      );
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.id).toBe(1);
    });

    it("returns null when row not found (no error)", async () => {
      const { client, chain } = makeClientWithChain();
      chain.maybeSingle.mockResolvedValue({ data: null, error: null });

      const { data, error } = await getMaybeSingle(client, "trips", (qb) => qb);
      expect(data).toBeNull();
      expect(error).toBeNull();
    });

    it("returns error when query fails", async () => {
      const { client, chain } = makeClientWithChain();
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
      const { client, chain } = makeClientWithChain();
      const payload: TablesInsert<"trips"> = {
        budget: 1500,
        destination: "LAX",
        end_date: "2025-03-15",
        name: "Upsert Trip",
        start_date: "2025-03-01",
        travelers: 2,
        user_id: userId,
      };
      const row = mockTripsRow({ ...payload, id: 5 });

      chain.single.mockResolvedValue({ data: row, error: null });

      const { data, error } = await upsertSingle(client, "trips", payload, "user_id");
      expect(error).toBeNull();
      expect(data).toBeTruthy();
      expect(data?.name).toBe("Upsert Trip");
      expect(data?.budget).toBe(1500);
    });

    it("returns error when upsert fails", async () => {
      const { client, chain } = makeClientWithChain();
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
          end_date: "2025-04-01",
          name: "Fail Upsert",
          start_date: "2025-03-01",
          travelers: 1,
          user_id: userId,
        },
        "user_id"
      );
      expect(data).toBeNull();
      expect(error).toBeTruthy();
    });
  });

  describe("upsertMany", () => {
    it("returns all upserted rows", async () => {
      const { client, chain } = makeClientWithChain();
      const payloads: TablesInsert<"trips">[] = [
        {
          budget: 1000,
          destination: "NYC",
          end_date: "2025-01-10",
          name: "Trip 1",
          start_date: "2025-01-01",
          travelers: 1,
          user_id: userId,
        },
        {
          budget: 2000,
          destination: "LAX",
          end_date: "2025-02-10",
          name: "Trip 2",
          start_date: "2025-02-01",
          travelers: 2,
          user_id: userId,
        },
      ];
      const rows = [
        mockTripsRow({ ...payloads[0], id: 10 }),
        mockTripsRow({ ...payloads[1], id: 11 }),
      ];

      const selectPromise = Promise.resolve({ data: rows, error: null });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, error } = await upsertMany(client, "trips", payloads, "user_id");
      expect(error).toBeNull();
      expect(data).toHaveLength(2);
      expect(data[0]?.id).toBe(10);
      expect(data[1]?.id).toBe(11);
    });

    it("returns error when upsert fails", async () => {
      const { client, chain } = makeClientWithChain();
      const payloads: TablesInsert<"trips">[] = [
        {
          budget: 1000,
          destination: "NYC",
          end_date: "2025-01-10",
          name: "Trip 1",
          start_date: "2025-01-01",
          travelers: 1,
          user_id: userId,
        },
      ];

      const selectPromise = Promise.resolve({
        data: null,
        error: { message: "Upsert failed" },
      });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, error } = await upsertMany(client, "trips", payloads, "user_id");
      expect(data).toHaveLength(0);
      expect(error).toBeTruthy();
    });
  });

  describe("getMany", () => {
    it("returns multiple rows", async () => {
      const { client, chain } = makeClientWithChain();
      const rows = [
        mockTripsRow({ id: 1, name: "Trip 1" }),
        mockTripsRow({ id: 2, name: "Trip 2" }),
        mockTripsRow({ id: 3, name: "Trip 3" }),
      ];

      // Mock the select chain to return rows when awaited
      const selectPromise = Promise.resolve({ count: null, data: rows, error: null });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, count, error } = await getMany(client, "trips", (qb) => qb);
      expect(error).toBeNull();
      expect(data).toHaveLength(3);
      expect(data[0]?.name).toBe("Trip 1");
      expect(count).toBeNull();
    });

    it("applies pagination with limit and offset", async () => {
      const { client, chain } = makeClientWithChain();
      const rows = [mockTripsRow({ id: 2 }), mockTripsRow({ id: 3 })];

      const selectPromise = Promise.resolve({ count: null, data: rows, error: null });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, error } = await getMany(client, "trips", (qb) => qb, {
        limit: 2,
        offset: 1,
      });
      expect(error).toBeNull();
      expect(chain.range).toHaveBeenCalledWith(1, 2);
      expect(data).toHaveLength(2);
    });

    it("applies ordering", async () => {
      const { client, chain } = makeClientWithChain();
      const rows = [
        mockTripsRow({ id: 3 }),
        mockTripsRow({ id: 2 }),
        mockTripsRow({ id: 1 }),
      ];

      const selectPromise = Promise.resolve({ count: null, data: rows, error: null });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, error } = await getMany(client, "trips", (qb) => qb, {
        ascending: false,
        orderBy: "id",
      });
      expect(error).toBeNull();
      expect(chain.order).toHaveBeenCalledWith("id", { ascending: false });
      expect(data).toHaveLength(3);
    });

    it("returns count when requested", async () => {
      const { client, chain } = makeClientWithChain();
      const rows = [mockTripsRow({ id: 1 })];

      const selectPromise = Promise.resolve({ count: 10, data: rows, error: null });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { count, data, error } = await getMany(client, "trips", (qb) => qb, {
        count: "exact",
        limit: 1,
      });
      expect(error).toBeNull();
      expect(data).toHaveLength(1);
      expect(count).toBe(10);
    });

    it("returns error when query fails", async () => {
      const { client, chain } = makeClientWithChain();

      const selectPromise = Promise.resolve({
        count: null,
        data: null,
        error: { message: "Query failed" },
      });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, error } = await getMany(client, "trips", (qb) => qb);
      expect(data).toHaveLength(0);
      expect(error).toBeTruthy();
    });
  });

  describe("insertMany", () => {
    it("returns all inserted rows", async () => {
      const { client, chain } = makeClientWithChain();
      const payloads: TablesInsert<"trips">[] = [
        {
          budget: 1000,
          destination: "NYC",
          end_date: "2025-01-10",
          name: "Trip 1",
          start_date: "2025-01-01",
          travelers: 1,
          user_id: userId,
        },
        {
          budget: 2000,
          destination: "LAX",
          end_date: "2025-02-10",
          name: "Trip 2",
          start_date: "2025-02-01",
          travelers: 2,
          user_id: userId,
        },
      ];
      const [first, second] = payloads;
      const rows = [
        mockTripsRow({ ...first, id: 1 }),
        mockTripsRow({ ...second, id: 2 }),
      ];

      // Mock the insert chain to return rows when select is called
      const selectPromise = Promise.resolve({ data: rows, error: null });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, error } = await insertMany(client, "trips", payloads);
      expect(error).toBeNull();
      expect(data).toHaveLength(2);
      expect(data[0]?.name).toBe("Trip 1");
      expect(data[1]?.name).toBe("Trip 2");
    });

    it("returns empty array when given empty input", async () => {
      const { client } = makeClientWithChain();

      const { data, error } = await insertMany(client, "trips", []);
      expect(error).toBeNull();
      expect(data).toHaveLength(0);
    });

    it("returns error when insert fails", async () => {
      const { client, chain } = makeClientWithChain();
      const payloads: TablesInsert<"trips">[] = [
        {
          budget: 1000,
          destination: "NYC",
          end_date: "2025-01-10",
          name: "Fail Trip",
          start_date: "2025-01-01",
          travelers: 1,
          user_id: userId,
        },
      ];

      const selectPromise = Promise.resolve({
        data: null,
        error: { message: "Insert failed" },
      });
      (chain.select as ReturnType<typeof vi.fn>).mockReturnValue(
        Object.assign(selectPromise, chain) as MockChain
      );

      const { data, error } = await insertMany(client, "trips", payloads);
      expect(data).toHaveLength(0);
      expect(error).toBeTruthy();
    });
  });
});
