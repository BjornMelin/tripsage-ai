import { bumpTag } from "@/lib/cache/tags";
import { createServerSupabase } from "@/lib/supabase/server";
import { describe, expect, it, vi } from "vitest";
import { addActivityToTrip, getPlanningTrips } from "./actions";

vi.mock("@/lib/supabase/server");
vi.mock("@/lib/cache/tags");

const mockUser = {
  id: "00000000-0000-0000-0000-000000000000",
  email: "test@example.com",
};

const mockTrips = [
  {
    id: 1,
    user_id: "00000000-0000-0000-0000-000000000000",
    name: "Trip to Paris",
    destination: "Paris",
    status: "planning",
    created_at: "2023-01-01T00:00:00Z",
    start_date: "2023-06-01T00:00:00Z",
    end_date: "2023-06-10T00:00:00Z",
    budget: 1000,
    currency: "USD",
    notes: [],
    travelers: 1,
    trip_type: "leisure",
    updated_at: "2023-01-01T00:00:00Z",
    flexibility: {},
  },
];

describe("search/activities/actions", () => {
  const mockSupabase = {
    auth: {
      getUser: vi.fn(),
    },
    from: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (createServerSupabase as any).mockResolvedValue(mockSupabase);
  });

  describe("getPlanningTrips", () => {
    it("should return planning trips for authenticated user", async () => {
      mockSupabase.auth.getUser.mockResolvedValue({ data: { user: mockUser } });
      
      const mockSelect = vi.fn().mockReturnThis();
      const mockEq = vi.fn().mockReturnThis();
      const mockIn = vi.fn().mockReturnThis();
      const mockOrder = vi.fn().mockResolvedValue({ data: mockTrips, error: null });

      mockSupabase.from.mockReturnValue({
        select: mockSelect,
        eq: mockEq,
        in: mockIn,
        order: mockOrder,
      } as any);

      const trips = await getPlanningTrips();

      expect(trips).toHaveLength(1);
      expect(trips[0].title).toBe("Trip to Paris");
      expect(mockSupabase.from).toHaveBeenCalledWith("trips");
      expect(mockEq).toHaveBeenCalledWith("user_id", mockUser.id);
      expect(mockIn).toHaveBeenCalledWith("status", ["planning", "active"]);
    });

    it("should throw error if unauthorized", async () => {
      mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null } });

      await expect(getPlanningTrips()).rejects.toThrow("Unauthorized");
    });
  });

  describe("addActivityToTrip", () => {
    it("should add activity to trip and invalidate cache", async () => {
      mockSupabase.auth.getUser.mockResolvedValue({ data: { user: mockUser } });

      // Mock trip check
      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi.fn().mockResolvedValue({ data: { id: 1 }, error: null });

      // Mock insert
      const mockInsert = vi.fn().mockResolvedValue({ error: null });

      mockSupabase.from.mockImplementation((table: string) => {
        if (table === "trips") {
          return {
            select: mockSelectTrip,
            eq: mockEqTrip,
            single: mockSingleTrip,
          } as any;
        }
        if (table === "itinerary_items") {
          return {
            insert: mockInsert,
          } as any;
        }
        return {} as any;
      });

      await addActivityToTrip(1, {
        title: "Eiffel Tower",
        description: "Visit the tower",
        price: 30,
      });

      expect(mockInsert).toHaveBeenCalledWith(expect.objectContaining({
        title: "Eiffel Tower",
        trip_id: 1,
        user_id: mockUser.id,
        item_type: "activity",
      }));
      expect(bumpTag).toHaveBeenCalledWith("trips");
    });

    it("should throw if trip not found", async () => {
      mockSupabase.auth.getUser.mockResolvedValue({ data: { user: mockUser } });

      // Mock trip check failure
      const mockSelectTrip = vi.fn().mockReturnThis();
      const mockEqTrip = vi.fn().mockReturnThis();
      const mockSingleTrip = vi.fn().mockResolvedValue({ data: null, error: { message: "Not found" } });

      mockSupabase.from.mockReturnValue({
        select: mockSelectTrip,
        eq: mockEqTrip,
        single: mockSingleTrip,
      } as any);

      await expect(addActivityToTrip(1, { title: "Test" })).rejects.toThrow("Trip not found");
    });
  });
});
