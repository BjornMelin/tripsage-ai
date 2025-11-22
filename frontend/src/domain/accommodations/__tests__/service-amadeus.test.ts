import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  type MockedFunction,
  vi,
} from "vitest";

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
import { getCachedJson } from "@/lib/cache/upstash";
import { getCachedLatLng } from "@/lib/google/caching";

describe("AccommodationsService (Amadeus)", () => {
  beforeEach(() => {
    fetchMock.mockResolvedValue({
      json: async () => ({
        places: [{ id: "places/abc", location: { latitude: 1.234, longitude: 2.345 } }],
      }),
      ok: true,
    });
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("injects geocoded lat/lng and maps provider search result", async () => {
    vi.mocked(getCachedLatLng).mockResolvedValue({ lat: 1.234, lon: 2.345 });
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
      supabase: async () =>
        ({}) as unknown as import("@/lib/supabase/server").TypedServerSupabase,
    });

    const result = await service.search({
      checkin: "2025-12-01",
      checkout: "2025-12-02",
      guests: 1,
      location: "Paris",
    });

    expect(result.searchParameters?.lat).toBeCloseTo(1.234);
    expect(result.searchParameters?.lng).toBeCloseTo(2.345);
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

    // Cache the place response so enrichment returns place/placeDetails without extra fetches
    vi.mocked(getCachedJson).mockResolvedValue({
      place: { id: "places/test", rating: 4.5 },
      placeDetails: { id: "places/test", rating: 4.5 },
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
      supabase: async () =>
        ({}) as unknown as import("@/lib/supabase/server").TypedServerSupabase,
    });

    const details = await service.details({ listingId: "H1" }, {});

    expect(details.listing).toMatchObject({
      place: expect.any(Object),
    });
  });
});
