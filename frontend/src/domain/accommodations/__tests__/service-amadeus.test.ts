import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Hoist mock so it can be accessed and modified in tests
const fetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: () => "test-key",
  getServerEnvVarWithFallback: () => undefined,
}));

vi.mock("@/lib/google/caching", () => ({
  cacheLatLng: vi.fn().mockResolvedValue(undefined),
  getCachedLatLng: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn().mockResolvedValue(null),
  setCachedJson: vi.fn().mockResolvedValue(undefined),
}));

import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { AccommodationsService } from "@domain/accommodations/service";

describe("AccommodationsService (Amadeus)", () => {
  beforeEach(() => {
    fetchMock.mockResolvedValue({
      json: async () => ({
        places: [{ id: "places/abc", location: { latitude: 1.234, longitude: 2.345 } }],
      }),
      ok: true,
    });
    // @ts-expect-error assign global
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("injects geocoded lat/lng and maps provider search result", async () => {
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn(),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn().mockResolvedValue({
        ok: true,
        retries: 0,
        value: {
          currency: "USD",
          listings: [
            {
              rooms: [
                {
                  rates: [
                    { price: { currency: "USD", numeric: 100, total: "100.00" } },
                  ],
                },
              ],
            },
          ],
          total: 1,
        },
      }),
    };

    const service = new AccommodationsService({
      cacheTtlSeconds: 0,
      provider,
      rateLimiter: undefined,
      supabase: async () => ({}) as any,
    });

    const result = await service.search({
      checkin: "2025-12-01",
      checkout: "2025-12-02",
      guests: 1,
      location: "Paris",
    });

    expect((provider.search as vi.Mock).mock.calls[0][0]).toMatchObject({
      lat: 1.234,
      lng: 2.345,
    });
    expect(result.provider).toBe("amadeus");
    expect(result.resultsReturned).toBe(1);
  });

  it("enriches details with Google Places when available", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({
        places: [{ id: "places/test", location: { latitude: 0, longitude: 0 } }],
      }),
      ok: true,
    });
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ id: "places/test", rating: 4.5 }),
      ok: true,
    });

    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn(),
      getDetails: vi.fn().mockResolvedValue({
        ok: true,
        retries: 0,
        value: {
          listing: {
            hotel: { address: { cityName: "Paris" }, name: "Test Hotel" },
          },
        },
      }),
      name: "amadeus",
      search: vi.fn(),
    };

    const service = new AccommodationsService({
      cacheTtlSeconds: 0,
      provider,
      rateLimiter: undefined,
      supabase: async () => ({}) as any,
    });

    const details = await service.details({ listingId: "H1" } as any, {});

    expect(details.listing).toMatchObject({
      place: expect.any(Object),
    });
  });
});
