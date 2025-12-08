/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Hoisted mocks per testing.md Pattern A
const mockFetchDuffelOffers = vi.hoisted(() => vi.fn());
const mockMapDuffelOffersList = vi.hoisted(() => vi.fn());

vi.mock("../providers/duffel", () => ({
  fetchDuffelOffers: mockFetchDuffelOffers,
}));

vi.mock("../mappers", () => ({
  mapDuffelOffersList: mockMapDuffelOffersList,
}));

import { searchFlightsService } from "../service";

describe("searchFlightsService", () => {
  const validRequest = {
    cabinClass: "economy" as const,
    currency: "USD",
    departureDate: "2025-06-15",
    destination: "CDG",
    origin: "JFK",
    passengers: 2,
  };

  const mockDuffelResponse = {
    data: {
      offers: [
        {
          id: "off_123",
          total_amount: "450.00",
          total_currency: "USD",
        },
      ],
    },
  };

  // Mock result matching flightSearchResultSchema
  const mockMappedResult = {
    currency: "USD",
    itineraries: [
      {
        id: "itn_123",
        price: 450,
        segments: [
          {
            arrival: "2025-06-16T08:00:00Z",
            carrier: "AF",
            departure: "2025-06-15T20:00:00Z",
            destination: "CDG",
            flightNumber: "AF123",
            origin: "JFK",
          },
        ],
      },
    ],
    offers: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchDuffelOffers.mockReset();
    mockMapDuffelOffersList.mockReset();
    mockFetchDuffelOffers.mockResolvedValue(mockDuffelResponse);
    mockMapDuffelOffersList.mockReturnValue(mockMappedResult);
  });

  describe("successful searches", () => {
    it("calls Duffel provider with parsed request", async () => {
      await searchFlightsService(validRequest);

      expect(mockFetchDuffelOffers).toHaveBeenCalledWith(
        expect.objectContaining({
          cabinClass: "economy",
          currency: "USD",
          departureDate: "2025-06-15",
          destination: "CDG",
          origin: "JFK",
          passengers: 2,
        })
      );
    });

    it("maps Duffel response to normalized format", async () => {
      await searchFlightsService(validRequest);

      expect(mockMapDuffelOffersList).toHaveBeenCalledWith(mockDuffelResponse, "USD");
    });

    it("returns properly structured flight search result", async () => {
      const result = await searchFlightsService(validRequest);

      expect(result).toMatchObject({
        currency: "USD",
        fromCache: false,
        itineraries: expect.any(Array),
        offers: expect.any(Array),
        provider: "duffel",
        schemaVersion: "flight.v2",
      });
    });

    it("includes itineraries in result", async () => {
      const result = await searchFlightsService(validRequest);

      expect(result.itineraries).toHaveLength(1);
      expect(result.itineraries[0]).toMatchObject({
        id: "itn_123",
        price: 450,
        segments: expect.arrayContaining([
          expect.objectContaining({
            destination: "CDG",
            origin: "JFK",
          }),
        ]),
      });
    });
  });

  describe("round trip searches", () => {
    it("handles round trip request with return date", async () => {
      const roundTripRequest = {
        ...validRequest,
        returnDate: "2025-06-22",
      };

      await searchFlightsService(roundTripRequest);

      expect(mockFetchDuffelOffers).toHaveBeenCalledWith(
        expect.objectContaining({
          returnDate: "2025-06-22",
        })
      );
    });
  });

  describe("nonstop preference", () => {
    it("passes nonstop preference to provider", async () => {
      const nonstopRequest = {
        ...validRequest,
        nonstop: true,
      };

      await searchFlightsService(nonstopRequest);

      expect(mockFetchDuffelOffers).toHaveBeenCalledWith(
        expect.objectContaining({
          nonstop: true,
        })
      );
    });
  });

  describe("cabin class options", () => {
    it.each([
      "economy",
      "premium_economy",
      "business",
      "first",
    ] as const)("accepts %s cabin class", async (cabinClass) => {
      const request = {
        ...validRequest,
        cabinClass,
      };

      await searchFlightsService(request);

      expect(mockFetchDuffelOffers).toHaveBeenCalledWith(
        expect.objectContaining({
          cabinClass,
        })
      );
    });
  });

  describe("input validation", () => {
    it("validates required fields", async () => {
      const invalidRequest = {
        currency: "USD",
        // Missing required fields
      };

      await expect(
        // @ts-expect-error - Testing invalid input
        searchFlightsService(invalidRequest)
      ).rejects.toThrow();
    });

    it("validates date format", async () => {
      const invalidDateRequest = {
        ...validRequest,
        departureDate: "invalid-date",
      };

      await expect(searchFlightsService(invalidDateRequest)).rejects.toThrow();
    });

    it("validates airport codes min length", async () => {
      const invalidAirportRequest = {
        ...validRequest,
        origin: "AB", // Less than 3 chars - should fail validation
      };

      await expect(searchFlightsService(invalidAirportRequest)).rejects.toThrow();
    });

    it("validates passenger count", async () => {
      const invalidPassengersRequest = {
        ...validRequest,
        passengers: 0,
      };

      await expect(searchFlightsService(invalidPassengersRequest)).rejects.toThrow();
    });
  });

  describe("error handling", () => {
    it("propagates Duffel API errors", async () => {
      const duffelError = new Error("duffel_offer_request_failed:401:Unauthorized");
      mockFetchDuffelOffers.mockRejectedValue(duffelError);

      await expect(searchFlightsService(validRequest)).rejects.toThrow(
        "duffel_offer_request_failed:401:Unauthorized"
      );
    });

    it("propagates configuration errors", async () => {
      const configError = new Error("Duffel API key is not configured");
      (configError as Error & { code?: string }).code = "duffel_not_configured";
      mockFetchDuffelOffers.mockRejectedValue(configError);

      await expect(searchFlightsService(validRequest)).rejects.toThrow(
        "Duffel API key is not configured"
      );
    });

    it("handles network errors", async () => {
      const networkError = new Error("fetch failed");
      mockFetchDuffelOffers.mockRejectedValue(networkError);

      await expect(searchFlightsService(validRequest)).rejects.toThrow("fetch failed");
    });

    it("handles mapping errors", async () => {
      mockMapDuffelOffersList.mockImplementation(() => {
        throw new Error("Failed to map offers");
      });

      await expect(searchFlightsService(validRequest)).rejects.toThrow(
        "Failed to map offers"
      );
    });

    it("handles schema validation errors in response", async () => {
      mockMapDuffelOffersList.mockReturnValue({
        // Invalid itinerary structure to trigger validation error
        currency: "USD",
        itineraries: [
          {
            id: "itn_123",
            // Missing required 'price' field
            segments: [],
          },
        ],
      });

      await expect(searchFlightsService(validRequest)).rejects.toThrow();
    });
  });

  describe("currency handling", () => {
    it.each(["USD", "EUR", "GBP", "JPY"])("supports %s currency", async (currency) => {
      mockMapDuffelOffersList.mockReturnValue({
        ...mockMappedResult,
        currency,
      });

      const request = { ...validRequest, currency };
      const result = await searchFlightsService(request);

      expect(result.currency).toBe(currency);
    });
  });

  describe("result structure", () => {
    it("sets fromCache to false for fresh results", async () => {
      const result = await searchFlightsService(validRequest);

      expect(result.fromCache).toBe(false);
    });

    it("sets provider to duffel", async () => {
      const result = await searchFlightsService(validRequest);

      expect(result.provider).toBe("duffel");
    });

    it("sets correct schema version", async () => {
      const result = await searchFlightsService(validRequest);

      expect(result.schemaVersion).toBe("flight.v2");
    });
  });
});
