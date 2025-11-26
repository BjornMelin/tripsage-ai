import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { bumpTag } from "@/lib/cache/tags";
import type { TypedSupabaseClient } from "@/lib/supabase";
import { createServerSupabase } from "@/lib/supabase/server";
import { addActivityToTrip, getPlanningTrips } from "./actions";

vi.mock("@/lib/supabase/server");
vi.mock("@/lib/cache/tags");

const mockUser = {
  email: "test@example.com",
  id: "00000000-0000-0000-0000-000000000000",
};

type TableClient = ReturnType<TypedSupabaseClient["from"]>;

const mockTrips = [
  {
    budget: 1000,
    created_at: "2023-01-01T00:00:00Z",
    currency: "USD",
    destination: "Paris",
    end_date: "2023-06-10T00:00:00Z",
    flexibility: {},
    id: 1,
    name: "Trip to Paris",
    notes: [],
    start_date: "2023-06-01T00:00:00Z",
    status: "planning",
    travelers: 1,
    trip_type: "leisure",
    updated_at: "2023-01-01T00:00:00Z",
    user_id: "00000000-0000-0000-0000-000000000000",
  },
];

describe("search/activities/actions", () => {
  const mockSupabase = {
    auth: {
      getUser: vi.fn(),
    },
    from: vi.fn(),
  } as unknown as TypedSupabaseClient;
  const mockFrom = mockSupabase.from as unknown as Mock;
  const mockGetUser = mockSupabase.auth.getUser as unknown as Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(createServerSupabase).mockResolvedValue(mockSupabase);
  });

  describe("getPlanningTrips", () => {
    it("should return planning trips for authenticated user", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      const mockSelect = vi.fn();
      const mockEq = vi.fn();
      const mockIn = vi.fn();
      const mockOrder = vi.fn().mockResolvedValue({ data: mockTrips, error: null });
      const queryBuilder = {
        eq: mockEq,
        in: mockIn,
        order: mockOrder,
        select: mockSelect,
      } as unknown as TableClient;

      mockSelect.mockReturnValue(queryBuilder);
      mockEq.mockReturnValue(queryBuilder);
      mockIn.mockReturnValue(queryBuilder);

      mockFrom.mockReturnValue(queryBuilder);

      const trips = await getPlanningTrips();

      expect(trips).toHaveLength(1);
      expect(trips[0].title).toBe("Trip to Paris");
      expect(mockSupabase.from).toHaveBeenCalledWith("trips");
      expect(queryBuilder.eq).toHaveBeenCalledWith("user_id", mockUser.id);
      expect(queryBuilder.in).toHaveBeenCalledWith("status", ["planning", "active"]);
      expect(queryBuilder.order).toHaveBeenCalledWith("created_at", {
        ascending: false,
      });
    });

    it("should throw error if unauthorized", async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } });

      await expect(getPlanningTrips()).rejects.toThrow("Unauthorized");
    });

    it("should throw error if fetch fails", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      const mockSelect = vi.fn();
      const mockEq = vi.fn();
      const mockIn = vi.fn();
      const mockOrder = vi.fn().mockResolvedValue({
        data: null,
        error: { message: "Database error" },
      });
      const queryBuilder = {
        eq: mockEq,
        in: mockIn,
        order: mockOrder,
        select: mockSelect,
      } as unknown as TableClient;

      mockSelect.mockReturnValue(queryBuilder);
      mockEq.mockReturnValue(queryBuilder);
      mockIn.mockReturnValue(queryBuilder);

      mockFrom.mockReturnValue(queryBuilder);

      await expect(getPlanningTrips()).rejects.toThrow("Failed to fetch trips");
    });
  });

  describe("addActivityToTrip", () => {
    it("should add activity to trip and invalidate cache", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      // Mock trip check
      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi
        .fn()
        .mockResolvedValue({ data: { id: 1 }, error: null });

      // Mock insert
      const mockInsert = vi.fn().mockResolvedValue({ error: null });

      mockFrom.mockImplementation((table: string) => {
        if (table === "trips") {
          return {
            eq: mockEqTrip,
            select: mockSelectTrip,
            single: mockSingleTrip,
          } as unknown as TableClient;
        }
        if (table === "itinerary_items") {
          return {
            insert: mockInsert,
          } as unknown as TableClient;
        }
        return {} as unknown as TableClient;
      });

      await addActivityToTrip(1, {
        description: "Visit the tower",
        price: 30,
        title: "Eiffel Tower",
      });

      expect(mockInsert).toHaveBeenCalledWith(
        expect.objectContaining({
          item_type: "activity",
          title: "Eiffel Tower",
          trip_id: 1,
          user_id: mockUser.id,
        })
      );
      expect(bumpTag).toHaveBeenCalledWith("trips");
    });

    it("coerces string trip ids to numbers for validation and insert", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi
        .fn()
        .mockResolvedValue({ data: { id: 1 }, error: null });

      const mockInsert = vi.fn().mockResolvedValue({ error: null });

      mockFrom.mockImplementation((table: string) => {
        if (table === "trips") {
          return {
            eq: mockEqTrip,
            select: mockSelectTrip,
            single: mockSingleTrip,
          } as unknown as TableClient;
        }
        if (table === "itinerary_items") {
          return {
            insert: mockInsert,
          } as unknown as TableClient;
        }
        return {} as unknown as TableClient;
      });

      await addActivityToTrip("1", {
        description: "Visit the tower",
        price: 30,
        title: "Eiffel Tower",
      });

      expect(mockInsert).toHaveBeenCalledWith(
        expect.objectContaining({
          trip_id: 1,
        })
      );
    });

    it("should handle optional fields when adding an activity", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi
        .fn()
        .mockResolvedValue({ data: { id: 1 }, error: null });

      const mockInsert = vi.fn().mockResolvedValue({ error: null });

      mockFrom.mockImplementation((table: string) => {
        if (table === "trips") {
          return {
            eq: mockEqTrip,
            select: mockSelectTrip,
            single: mockSingleTrip,
          } as unknown as TableClient;
        }
        if (table === "itinerary_items") {
          return {
            insert: mockInsert,
          } as unknown as TableClient;
        }
        return {} as unknown as TableClient;
      });

      await addActivityToTrip(1, {
        currency: "EUR",
        description: "City tour",
        endTime: "2023-06-01T12:00:00Z",
        externalId: "ext-123",
        location: "Downtown",
        metadata: { provider: "TourCo" },
        price: 50,
        startTime: "2023-06-01T10:00:00Z",
        title: "Tour",
      });

      expect(mockInsert).toHaveBeenCalledWith(
        expect.objectContaining({
          currency: "EUR",
          description: "City tour",
          end_time: "2023-06-01T12:00:00Z",
          external_id: "ext-123",
          item_type: "activity",
          location: "Downtown",
          metadata: { provider: "TourCo" },
          price: 50,
          start_time: "2023-06-01T10:00:00Z",
          title: "Tour",
        })
      );
    });

    it("should succeed even if cache invalidation fails", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi
        .fn()
        .mockResolvedValue({ data: { id: 1 }, error: null });

      const mockInsert = vi.fn().mockResolvedValue({ error: null });

      mockFrom.mockImplementation((table: string) => {
        if (table === "trips") {
          return {
            eq: mockEqTrip,
            select: mockSelectTrip,
            single: mockSingleTrip,
          } as unknown as TableClient;
        }
        if (table === "itinerary_items") {
          return {
            insert: mockInsert,
          } as unknown as TableClient;
        }
        return {} as unknown as TableClient;
      });

      vi.mocked(bumpTag).mockRejectedValue(new Error("cache failure"));

      await expect(
        addActivityToTrip(1, {
          description: "Visit the tower",
          price: 30,
          title: "Eiffel Tower",
        })
      ).resolves.not.toThrow();

      expect(mockInsert).toHaveBeenCalled();
    });

    it("should throw if trip not found", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      // Mock trip check failure
      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi
        .fn()
        .mockResolvedValue({ data: null, error: { message: "Not found" } });

      mockFrom.mockReturnValue({
        eq: mockEqTrip,
        select: mockSelectTrip,
        single: mockSingleTrip,
      } as unknown as TableClient);

      await expect(addActivityToTrip(1, { title: "Test" })).rejects.toThrow(
        "Trip not found or access denied"
      );
    });

    it("should throw if unauthorized", async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } });

      await expect(addActivityToTrip(1, { title: "Test" })).rejects.toThrow(
        "Unauthorized"
      );
    });

    it("should throw if activity data is invalid", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi
        .fn()
        .mockResolvedValue({ data: { id: 1 }, error: null });

      const mockInsert = vi.fn();

      mockFrom.mockImplementation((table: string) => {
        if (table === "trips") {
          return {
            eq: mockEqTrip,
            select: mockSelectTrip,
            single: mockSingleTrip,
          } as unknown as TableClient;
        }
        if (table === "itinerary_items") {
          return {
            insert: mockInsert,
          } as unknown as TableClient;
        }
        return {} as unknown as TableClient;
      });

      await expect(addActivityToTrip(1, { title: "" })).rejects.toThrow(
        /Invalid activity data/
      );

      expect(mockInsert).not.toHaveBeenCalled();
      expect(bumpTag).not.toHaveBeenCalled();
    });

    it("should throw if insert fails", async () => {
      mockGetUser.mockResolvedValue({ data: { user: mockUser } });

      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi
        .fn()
        .mockResolvedValue({ data: { id: 1 }, error: null });

      const mockInsert = vi
        .fn()
        .mockResolvedValue({ error: { code: "500", message: "insert failed" } });

      mockFrom.mockImplementation((table: string) => {
        if (table === "trips") {
          return {
            eq: mockEqTrip,
            select: mockSelectTrip,
            single: mockSingleTrip,
          } as unknown as TableClient;
        }
        if (table === "itinerary_items") {
          return {
            insert: mockInsert,
          } as unknown as TableClient;
        }
        return {} as unknown as TableClient;
      });

      await expect(
        addActivityToTrip(1, {
          description: "Visit the tower",
          price: 30,
          title: "Eiffel Tower",
        })
      ).rejects.toThrow("Failed to add activity to trip: insert failed");

      expect(bumpTag).not.toHaveBeenCalled();
    });

    it("should reject non-numeric trip ids", async () => {
      await expect(
        addActivityToTrip("invalid-id" as unknown as number, {
          title: "Invalid",
        })
      ).rejects.toThrow("Invalid trip id");
    });
  });
});
