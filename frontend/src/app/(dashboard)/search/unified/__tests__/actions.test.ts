/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock server-only module
vi.mock("server-only", () => ({}));

// Mock telemetry
const withTelemetrySpanSpy = vi.hoisted(() => vi.fn((_name, _attrs, fn) => fn()));
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: withTelemetrySpanSpy,
}));

// Mock secure UUID
vi.mock("@/lib/security/random", () => ({
  secureUuid: vi.fn(() => "mock-uuid-123"),
}));

// Mock Google Maps key
vi.mock("@/lib/env/client", () => ({
  getGoogleMapsBrowserKey: vi.fn(() => "mock-api-key"),
}));

// Mock accommodations service
const mockSearch = vi.hoisted(() => vi.fn());
vi.mock("@domain/accommodations/container", () => ({
  getAccommodationsService: () => ({
    search: mockSearch,
  }),
}));

// Import after mocks
import { searchHotelsAction } from "../actions";

describe("searchHotelsAction", () => {
  const validParams = {
    adults: 2,
    amenities: [] as string[],
    checkIn: "2025-06-01",
    checkOut: "2025-06-05",
    children: 0,
    location: "Paris, France",
    priceRange: { max: 500, min: 100 },
    rating: 0,
    rooms: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockSearch.mockResolvedValue({ listings: [] });
  });

  it("propagates errors from the accommodations service", async () => {
    const error = new Error("search failed");
    mockSearch.mockRejectedValue(error);

    await expect(searchHotelsAction(validParams)).rejects.toThrow("search failed");
  });

  it("returns empty array when no listings found", async () => {
    mockSearch.mockResolvedValue({ listings: [] });

    const result = await searchHotelsAction(validParams);

    expect(result).toEqual([]);
  });

  it("calls accommodations service with correct parameters", async () => {
    mockSearch.mockResolvedValue({ listings: [] });

    await searchHotelsAction(validParams);

    expect(mockSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        checkin: "2025-06-01",
        checkout: "2025-06-05",
        guests: 2,
        location: "Paris, France",
        priceMax: 500,
        priceMin: 100,
      }),
      expect.objectContaining({
        sessionId: "mock-uuid-123",
      })
    );

    expect(withTelemetrySpanSpy).toHaveBeenCalledWith(
      "ui.unified.searchHotels",
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("limits results to 10 hotels", async () => {
    const manyListings = Array.from({ length: 15 }, (_, i) => ({
      id: `hotel-${i}`,
      name: `Hotel ${i}`,
      starRating: 4,
    }));
    mockSearch.mockResolvedValue({ listings: manyListings });

    const result = await searchHotelsAction(validParams);

    expect(result).toHaveLength(10);
  });

  it("transforms valid listing to HotelResult", async () => {
    const listing = {
      address: {
        cityName: "Paris",
        lines: ["123 Champs-Élysées"],
      },
      amenities: ["wifi", "pool", "spa"],
      id: "hotel-1",
      name: "Grand Paris Hotel",
      place: {
        rating: 4.8,
        userRatingCount: 250,
      },
      rooms: [
        {
          rates: [
            {
              price: {
                base: "700",
                currency: "EUR",
                taxes: [{ amount: "100" }],
                total: "800",
              },
            },
          ],
          roomsLeft: 2,
        },
      ],
      starRating: 5,
    };
    mockSearch.mockResolvedValue({ listings: [listing] });

    const result = await searchHotelsAction(validParams);

    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      amenities: expect.objectContaining({
        essential: ["wifi", "pool", "spa"],
      }),
      category: "hotel",
      id: "hotel-1",
      location: expect.objectContaining({
        address: "123 Champs-Élysées",
        city: "Paris",
      }),
      name: "Grand Paris Hotel",
      pricing: expect.objectContaining({
        currency: "EUR",
        totalPrice: 800,
      }),
      reviewCount: 250,
      starRating: 5,
      userRating: 4.8,
    });
  });

  it("handles listing without rooms gracefully", async () => {
    const listing = {
      id: "hotel-2",
      name: "Budget Hotel",
      starRating: 3,
    };
    mockSearch.mockResolvedValue({ listings: [listing] });

    const result = await searchHotelsAction(validParams);

    expect(result).toHaveLength(1);
    expect(result[0].pricing.totalPrice).toBe(0);
  });

  it("calculates nights correctly", async () => {
    const listing = {
      id: "hotel-1",
      name: "Test Hotel",
      rooms: [
        {
          rates: [
            {
              price: {
                currency: "USD",
                total: "400",
              },
            },
          ],
        },
      ],
    };
    mockSearch.mockResolvedValue({ listings: [listing] });

    // 4 nights: June 1-5
    const result = await searchHotelsAction(validParams);

    expect(result[0].pricing.pricePerNight).toBe(100); // 400 / 4 nights
  });

  it("handles same-day check-in/check-out as 1 night minimum", async () => {
    const listing = {
      id: "hotel-1",
      name: "Test Hotel",
      rooms: [
        {
          rates: [
            {
              price: {
                currency: "USD",
                total: "100",
              },
            },
          ],
        },
      ],
    };
    mockSearch.mockResolvedValue({ listings: [listing] });

    // Same day check-in and check-out results in 0 diff, should use 1 night minimum
    const paramsWithSameDay = {
      ...validParams,
      checkIn: "2025-06-01",
      checkOut: "2025-06-01",
    };

    const result = await searchHotelsAction(paramsWithSameDay);

    // Math.ceil(0) = 0, but Math.max(1, 0) = 1 night minimum
    expect(result[0].pricing.pricePerNight).toBe(100);
  });

  it("returns a fallback result when listing validation fails", async () => {
    const invalidListing = {
      invalid: "value",
    };
    mockSearch.mockResolvedValue({ listings: [invalidListing] });

    const result = await searchHotelsAction(validParams);

    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      ai: expect.objectContaining({
        personalizedTags: ["hybrid-amadeus", "google-places"],
        recommendation: 8,
      }),
      amenities: { essential: [], premium: [], unique: [] },
      category: "hotel",
      id: "mock-uuid-123",
      name: "Hotel",
      pricing: expect.objectContaining({
        currency: "USD",
        pricePerNight: 0,
        totalPrice: 0,
      }),
      reviewCount: 0,
      starRating: 0,
      userRating: 0,
    });
  });

  it("uses default currency when not specified in listing", async () => {
    const listing = {
      id: "hotel-1",
      name: "Test Hotel",
    };
    mockSearch.mockResolvedValue({ listings: [listing] });

    const result = await searchHotelsAction(validParams);

    expect(result[0].pricing.currency).toBe("USD");
  });

  it("prefers listing currency over default", async () => {
    const listing = {
      id: "hotel-1",
      name: "Test Hotel",
      rooms: [
        {
          rates: [
            {
              price: {
                currency: "JPY",
                total: "10000",
              },
            },
          ],
        },
      ],
    };
    mockSearch.mockResolvedValue({ listings: [listing] });

    const result = await searchHotelsAction(validParams);

    expect(result[0].pricing.currency).toBe("JPY");
  });

  it("includes AI recommendation metadata", async () => {
    const listing = {
      id: "hotel-1",
      name: "AI Recommended Hotel",
    };
    mockSearch.mockResolvedValue({ listings: [listing] });

    const result = await searchHotelsAction(validParams);

    expect(result[0].ai).toMatchObject({
      personalizedTags: expect.arrayContaining(["hybrid-amadeus", "google-places"]),
      reason: expect.any(String),
      recommendation: 8,
    });
  });
});
