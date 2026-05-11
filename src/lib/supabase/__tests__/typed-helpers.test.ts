/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { Tables, TablesInsert, TablesUpdate } from "@/lib/supabase/database.types";
import type { TypedClient } from "@/lib/supabase/typed-helpers";
import {
  deleteMany,
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
  eq: ReturnType<typeof vi.fn>;
  in: ReturnType<typeof vi.fn>;
  insert: ReturnType<typeof vi.fn>;
  limit: ReturnType<typeof vi.fn>;
  maybeSingle: ReturnType<typeof vi.fn>;
  order: ReturnType<typeof vi.fn>;
  range: ReturnType<typeof vi.fn>;
  select: ReturnType<typeof vi.fn>;
  single: ReturnType<typeof vi.fn>;
  update: ReturnType<typeof vi.fn>;
  upsert: ReturnType<typeof vi.fn>;
};

function makeMockFrom(): MockChain {
  const chain: MockChain = {
    delete: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    in: vi.fn().mockReturnThis(),
    insert: vi.fn().mockReturnThis(),
    limit: vi.fn().mockReturnThis(),
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

function mockQueryResult<Result extends object>(
  chain: MockChain,
  method: "delete" | "select" | "update",
  result: Result
): MockChain {
  const queryPromise = Promise.resolve(result);
  const queryChain = Object.assign(queryPromise, chain) as MockChain;
  chain[method].mockReturnValue(queryChain);
  return queryChain;
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

    it("rejects validation for tables without registered Zod schemas", async () => {
      const { client, chain } = makeClientWithChain();
      const unsupportedTable = unsafeCast<"trips">("unsupported_table");
      const payload: TablesInsert<"trips"> = {
        budget: 100,
        destination: "LAX",
        end_date: "2025-02-01",
        name: "Unsupported Trip",
        start_date: "2025-01-01",
        travelers: 1,
        user_id: userId,
      };

      const { data, error } = await insertSingle(client, unsupportedTable, payload);

      expect(data).toBeNull();
      expect(error).toBeInstanceOf(Error);
      expect((error as Error).message).toBe(
        "unsupported_table_for_validation:public.unsupported_table"
      );
      expect(chain.insert).not.toHaveBeenCalled();
    });

    it("allows generated tables without Zod schemas when validation is disabled", async () => {
      const { client, chain } = makeClientWithChain();
      const payload: TablesInsert<"bookings"> = {
        checkin: "2025-01-01",
        checkout: "2025-01-02",
        guest_email: "guest@example.com",
        guest_name: "Guest User",
        guests: 1,
        id: "booking-1",
        property_id: "hotel-1",
        provider_booking_id: "provider-booking-1",
        status: "pending",
        trip_id: 1,
        user_id: userId,
      };

      chain.single.mockResolvedValue({
        data: unsafeCast<Tables<"bookings">>({ id: "booking-1" }),
        error: null,
      });

      const { data, error } = await insertSingle(client, "bookings", payload, {
        select: "id",
        validate: false,
      });

      expect(error).toBeNull();
      expect(data?.id).toBe("booking-1");
      expect(chain.insert).toHaveBeenCalledWith(payload);
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

    it("supports partial selects when validation is disabled", async () => {
      const { client, chain } = makeClientWithChain();
      chain.single.mockResolvedValue({
        data: unsafeCast<Tables<"trips">>({ id: 7 }),
        error: null,
      });

      const result = await updateSingle(
        client,
        "trips",
        { name: "Updated" },
        (qb) => qb.eq("id", 7),
        {
          select: "id",
          validate: false,
        }
      );

      expect(result.error).toBeNull();
      expect(chain.select).toHaveBeenCalledWith("id");
      expect(result.data?.id).toBe(7);
    });
  });

  describe("updateMany", () => {
    it("returns count when update succeeds", async () => {
      const { client, chain } = makeClientWithChain();
      const updates: Partial<TablesUpdate<"trips">> = { status: "completed" };

      mockQueryResult(chain, "update", { count: 2, error: null });

      const { count, error } = await updateMany(client, "trips", updates, (qb) =>
        qb.eq("status", "planning")
      );
      expect(error).toBeNull();
      expect(count).toBe(2);
    });

    it("omits count preference when count is null", async () => {
      const { client, chain } = makeClientWithChain();
      const updates: Partial<TablesUpdate<"trips">> = { status: "completed" };

      mockQueryResult(chain, "update", { count: 0, error: null });

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

      mockQueryResult(chain, "update", {
        count: 0,
        error: { message: "Update failed" },
      });

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
      mockQueryResult(chain, "select", {
        count: 1,
        data: [{ id: 1 }],
        error: null,
      });
      mockQueryResult(chain, "delete", { count: 1, error: null });

      const { count, error } = await deleteSingle(client, "trips", (qb) =>
        qb.eq("id", 1)
      );
      expect(count).toBe(1);
      expect(error).toBeNull();
      expect(chain.delete).toHaveBeenCalledWith({ count: "exact" });
      expect(chain.limit).toHaveBeenCalledWith(1);
    });

    it("allows zero-row deletes so callers can return not found", async () => {
      const { client, chain } = makeClientWithChain();
      mockQueryResult(chain, "select", {
        count: 0,
        data: [],
        error: null,
      });

      const { count, error } = await deleteSingle(client, "trips", (qb) =>
        qb.eq("id", 404)
      );
      expect(count).toBe(0);
      expect(error).toBeNull();
      expect(chain.delete).not.toHaveBeenCalled();
    });

    it("rejects no-count deletes", async () => {
      const { client, chain } = makeClientWithChain();

      const { count, error } = await deleteSingle(client, "trips", (qb) => qb, {
        count: null,
      });

      expect(count).toBe(0);
      expect(error).toBeInstanceOf(Error);
      expect((error as Error).message).toBe("delete_single_requires_count");
      expect(chain.delete).not.toHaveBeenCalled();
    });

    it("returns an error when more than one row matches", async () => {
      const { client, chain } = makeClientWithChain();
      mockQueryResult(chain, "select", {
        count: 2,
        data: [{ id: 1 }, { id: 2 }],
        error: null,
      });

      const { count, error } = await deleteSingle(client, "trips", (qb) =>
        qb.in("id", [1, 2])
      );

      expect(count).toBe(2);
      expect(error).toBeInstanceOf(Error);
      expect((error as Error).message).toBe("delete_single_matched_multiple_rows");
      expect(chain.delete).not.toHaveBeenCalled();
    });

    it("returns an error if the delete result reports multiple rows after preflight", async () => {
      const { client, chain } = makeClientWithChain();
      mockQueryResult(chain, "select", {
        count: 1,
        data: [{ id: 1 }],
        error: null,
      });
      mockQueryResult(chain, "delete", { count: 2, error: null });

      const { count, error } = await deleteSingle(client, "trips", (qb) =>
        qb.eq("status", "planning")
      );

      expect(count).toBe(2);
      expect(error).toBeInstanceOf(Error);
      expect((error as Error).message).toBe("delete_single_matched_multiple_rows");
      expect(chain.limit).toHaveBeenCalledWith(1);
    });

    it("returns error when delete fails", async () => {
      const { client, chain } = makeClientWithChain();
      const deleteError = { message: "Delete failed" };
      mockQueryResult(chain, "select", {
        count: 1,
        data: [{ id: 1 }],
        error: null,
      });
      mockQueryResult(chain, "delete", { count: 0, error: deleteError });

      const { count, error } = await deleteSingle(client, "trips", (qb) => qb);
      expect(count).toBe(0);
      expect(error).toBeTruthy();
    });
  });

  describe("deleteMany", () => {
    it("omits count preference when count is null", async () => {
      const { client, chain } = makeClientWithChain();
      mockQueryResult(chain, "delete", { count: 0, error: null });

      const { count, error } = await deleteMany(
        client,
        "trips",
        (qb) => qb.in("id", [1, 2]),
        { count: null }
      );
      expect(count).toBe(0);
      expect(error).toBeNull();
      expect(chain.delete).toHaveBeenCalledWith();
    });

    it("allows multi-row deletes", async () => {
      const { client, chain } = makeClientWithChain();
      mockQueryResult(chain, "delete", { count: 3, error: null });

      const { count, error } = await deleteMany(client, "trips", (qb) =>
        qb.eq("status", "cancelled")
      );

      expect(count).toBe(3);
      expect(error).toBeNull();
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

      mockQueryResult(chain, "select", { data: rows, error: null });

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

      mockQueryResult(chain, "select", {
        data: null,
        error: { message: "Upsert failed" },
      });

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

      mockQueryResult(chain, "select", { count: null, data: rows, error: null });

      const { data, count, error } = await getMany(client, "trips", (qb) => qb);
      expect(error).toBeNull();
      expect(data).toHaveLength(3);
      expect(data[0]?.name).toBe("Trip 1");
      expect(count).toBeNull();
    });

    it("applies pagination with limit and offset", async () => {
      const { client, chain } = makeClientWithChain();
      const rows = [mockTripsRow({ id: 2 }), mockTripsRow({ id: 3 })];

      mockQueryResult(chain, "select", { count: null, data: rows, error: null });

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

      mockQueryResult(chain, "select", { count: null, data: rows, error: null });

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

      mockQueryResult(chain, "select", { count: 10, data: rows, error: null });

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

      mockQueryResult(chain, "select", {
        count: null,
        data: null,
        error: { message: "Query failed" },
      });

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

      mockQueryResult(chain, "select", { data: rows, error: null });

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

      mockQueryResult(chain, "select", {
        data: null,
        error: { message: "Insert failed" },
      });

      const { data, error } = await insertMany(client, "trips", payloads);
      expect(data).toHaveLength(0);
      expect(error).toBeTruthy();
    });
  });
});
