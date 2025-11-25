import { describe, expect, it, type Mock, vi } from "vitest";
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

      const mockSelect = vi.fn().mockReturnThis();
      const mockEq = vi.fn().mockReturnThis();
      const mockIn = vi.fn().mockReturnThis();
      const mockOrder = vi.fn().mockResolvedValue({ data: mockTrips, error: null });

      mockFrom.mockReturnValue({
        eq: mockEq,
        in: mockIn,
        order: mockOrder,
        select: mockSelect,
      } as unknown as TableClient);

      const trips = await getPlanningTrips();

      expect(trips).toHaveLength(1);
      expect(trips[0].title).toBe("Trip to Paris");
      expect(mockSupabase.from).toHaveBeenCalledWith("trips");
      expect(mockEq).toHaveBeenCalledWith("user_id", mockUser.id);
      expect(mockIn).toHaveBeenCalledWith("status", ["planning", "active"]);
    });

    it("should throw error if unauthorized", async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } });

      await expect(getPlanningTrips()).rejects.toThrow("Unauthorized");
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
        "Trip not found"
      );
    });
  });
});
