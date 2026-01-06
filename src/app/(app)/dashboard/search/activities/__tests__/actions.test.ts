/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => {
  vi.clearAllMocks();
});

// Mock supabase server client
const mockGetUser = vi.fn();
const mockFrom = vi.fn();
const mapDbTripToUi = vi.hoisted(() =>
  vi.fn((row: Record<string, unknown>) => ({
    ...row,
    mapped: true,
  }))
);
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(() =>
    Promise.resolve({
      auth: {
        getUser: mockGetUser,
      },
      from: mockFrom,
    })
  ),
}));

// Mock cache tags
vi.mock("@/lib/cache/tags", () => ({
  bumpTag: vi.fn(() => Promise.resolve()),
}));

// Mock logger
vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  })),
}));

// Mock trip mapper
vi.mock("@/lib/trips/mappers", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/trips/mappers")>();
  return {
    ...actual,
    mapDbTripToUi,
  };
});

// Dynamic import after mocks
const { getPlanningTrips, addActivityToTrip } = await import("../actions");
const { bumpTag } = await import("@/lib/cache/tags");

// Helper to create a valid trips row that passes schema validation
function createValidTripRow(overrides: Record<string, unknown> = {}) {
  return {
    budget: 1000,
    created_at: "2024-01-01T00:00:00Z",
    currency: "USD",
    destination: "Paris",
    end_date: "2024-02-01T00:00:00Z",
    flexibility: null,
    id: 1,
    name: "Test Trip",
    search_metadata: null,
    start_date: "2024-01-15T00:00:00Z",
    status: "planning",
    tags: null,
    travelers: 2,
    trip_type: "leisure",
    updated_at: "2024-01-01T00:00:00Z",
    user_id: "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    ...overrides,
  };
}

describe("Activity actions - getPlanningTrips", () => {
  it("returns Unauthorized when user is not authenticated", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });

    const result = await getPlanningTrips();
    expect(result.ok).toBe(false);
  });

  it("returns empty array when no trips exist", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    mockFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            order: vi.fn().mockResolvedValue({ data: [], error: null }),
          }),
        }),
      }),
    });

    const result = await getPlanningTrips();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(Array.isArray(result.data)).toBe(true);
      expect(result.data).toEqual([]);
    }
  });

  it("returns error when database query fails", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    mockFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            order: vi.fn().mockResolvedValue({
              data: null,
              error: { details: "Connection timeout", message: "Database error" },
            }),
          }),
        }),
      }),
    });

    const result = await getPlanningTrips();
    expect(result.ok).toBe(false);
  });

  it("returns mapped trips when query succeeds", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    // Create a valid trip row that passes tripsRowSchema validation
    const validRow = createValidTripRow({ id: 1, name: "First Trip" });
    mockFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            order: vi.fn().mockResolvedValue({ data: [validRow], error: null }),
          }),
        }),
      }),
    });

    const result = await getPlanningTrips();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("Expected ok result");
    }

    expect(result.data).toHaveLength(1);
    // .map() calls with (element, index, array), so verify first argument only
    expect(mapDbTripToUi).toHaveBeenCalled();
    expect(mapDbTripToUi.mock.calls[0][0]).toEqual(validRow);
    expect(result.data[0]).toMatchObject({ mapped: true });
  });
});

describe("Activity actions - addActivityToTrip", () => {
  it("returns error for non-numeric trip id string", async () => {
    const result = await addActivityToTrip("invalid-id", {
      title: "Test Activity",
    });
    expect(result.ok).toBe(false);
  });

  it("returns Unauthorized when user is not authenticated", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });

    const result = await addActivityToTrip(123, {
      title: "Beach Tour",
    });
    expect(result.ok).toBe(false);
  });

  it("returns error when trip not found or access denied", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    mockFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            single: vi.fn().mockResolvedValue({
              data: null,
              error: { message: "No rows found" },
            }),
          }),
        }),
      }),
    });

    const result = await addActivityToTrip(123, {
      title: "Beach Tour",
    });
    expect(result.ok).toBe(false);
  });

  it("inserts activity successfully", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    const mockInsert = vi.fn().mockResolvedValue({ error: null });
    mockFrom.mockReturnValue({
      insert: mockInsert,
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            single: vi.fn().mockResolvedValue({ data: { id: 123 }, error: null }),
          }),
        }),
      }),
    });

    const result = await addActivityToTrip(123, {
      currency: "USD",
      description: "A fun beach tour",
      price: 99.99,
      title: "Beach Tour",
    });
    expect(result.ok).toBe(true);

    expect(mockInsert).toHaveBeenCalledTimes(1);
    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        currency: "USD",
        description: "A fun beach tour",
        price: 99.99,
        title: "Beach Tour",
        trip_id: 123,
        user_id: "test-user",
      })
    );
  });

  it("coerces numeric trip id strings and inserts with number trip_id", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    const mockInsert = vi.fn().mockResolvedValue({ error: null });

    mockFrom.mockImplementation((table: string) => {
      if (table === "trips") {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({ data: { id: 1 }, error: null }),
              }),
            }),
          }),
        };
      }
      if (table === "itinerary_items") {
        return { insert: mockInsert };
      }
      return {};
    });

    const result = await addActivityToTrip("1", { title: "Beach Tour" });
    expect(result.ok).toBe(true);

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        trip_id: 1,
      })
    );
  });

  it("returns error when activity data fails validation", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    const mockInsert = vi.fn();
    const single = vi.fn().mockResolvedValue({ data: { id: 123 }, error: null });
    mockFrom.mockReturnValue({
      insert: mockInsert,
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({ single }),
        }),
      }),
    });

    const result = await addActivityToTrip(123, {
      title: "", // invalid per schema
    });
    expect(result.ok).toBe(false);

    expect(mockInsert).not.toHaveBeenCalled();
  });

  it("maps optional activity fields and inserts snake_case columns", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    const mockInsert = vi.fn().mockResolvedValue({ error: null });

    mockFrom.mockImplementation((table: string) => {
      if (table === "trips") {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({ data: { id: 123 }, error: null }),
              }),
            }),
          }),
        };
      }
      if (table === "itinerary_items") {
        return { insert: mockInsert };
      }
      return {};
    });

    const result = await addActivityToTrip(123, {
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
    expect(result.ok).toBe(true);

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        currency: "EUR",
        description: "City tour",
        end_time: "2023-06-01T12:00:00Z",
        external_id: "ext-123",
        location: "Downtown",
        metadata: { provider: "TourCo" },
        price: 50,
        start_time: "2023-06-01T10:00:00Z",
        title: "Tour",
      })
    );
  });

  it("succeeds even if cache invalidation fails", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    vi.mocked(bumpTag).mockRejectedValueOnce(new Error("cache failure"));

    const mockInsert = vi.fn().mockResolvedValue({ error: null });
    mockFrom.mockImplementation((table: string) => {
      if (table === "trips") {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({ data: { id: 123 }, error: null }),
              }),
            }),
          }),
        };
      }
      if (table === "itinerary_items") {
        return { insert: mockInsert };
      }
      return {};
    });

    const result = await addActivityToTrip(123, { title: "Beach Tour" });
    expect(result.ok).toBe(true);
    expect(mockInsert).toHaveBeenCalledTimes(1);
  });

  it("returns error when insert fails and does not bump cache tag", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "test-user" } } });
    const mockInsert = vi.fn().mockResolvedValue({
      error: { code: "500", details: "insert failed", message: "insert failed" },
    });
    mockFrom.mockImplementation((table: string) => {
      if (table === "trips") {
        return {
          select: vi.fn().mockReturnValue({
            eq: vi.fn().mockReturnValue({
              eq: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({ data: { id: 123 }, error: null }),
              }),
            }),
          }),
        };
      }
      if (table === "itinerary_items") {
        return { insert: mockInsert };
      }
      return {};
    });

    const result = await addActivityToTrip(123, { title: "Beach Tour" });
    expect(result.ok).toBe(false);
    expect(vi.mocked(bumpTag)).not.toHaveBeenCalled();
  });
});
