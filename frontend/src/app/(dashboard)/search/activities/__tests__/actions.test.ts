/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

// Mock supabase server client
const mockGetUser = vi.fn();
const mockFrom = vi.fn();
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
vi.mock("@/lib/trips/mappers", () => ({
  mapDbTripToUi: vi.fn((row) => ({
    ...row,
    mapped: true,
  })),
}));

// Dynamic import after mocks
const { getPlanningTrips, addActivityToTrip } = await import("../actions");

describe("Activity actions - getPlanningTrips", () => {
  it("throws Unauthorized when user is not authenticated", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });

    await expect(getPlanningTrips()).rejects.toThrow("Unauthorized");
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

    expect(Array.isArray(result)).toBe(true);
    expect(result).toEqual([]);
  });

  it("throws error when database query fails", async () => {
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

    await expect(getPlanningTrips()).rejects.toThrow("Failed to fetch trips");
  });
});

describe("Activity actions - addActivityToTrip", () => {
  it("throws error for non-numeric trip id string", async () => {
    await expect(
      addActivityToTrip("invalid-id", {
        title: "Test Activity",
      })
    ).rejects.toThrow("Invalid trip id");
  });

  it("throws Unauthorized when user is not authenticated", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });

    await expect(
      addActivityToTrip(123, {
        title: "Beach Tour",
      })
    ).rejects.toThrow("Unauthorized");
  });

  it("throws error when trip not found or access denied", async () => {
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

    await expect(
      addActivityToTrip(123, {
        title: "Beach Tour",
      })
    ).rejects.toThrow("Trip not found or access denied");
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

    await expect(
      addActivityToTrip(123, {
        currency: "USD",
        description: "A fun beach tour",
        price: 99.99,
        title: "Beach Tour",
      })
    ).resolves.toBeUndefined();
  });
});
