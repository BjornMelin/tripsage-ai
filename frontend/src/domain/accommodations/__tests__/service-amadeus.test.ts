/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildUpstashCacheMock } from "@/test/mocks";
import { server } from "@/test/msw/server";

vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: () => "test-key",
  getServerEnvVarWithFallback: () => undefined,
}));

vi.mock("@/lib/google/caching", () => ({
  cacheLatLng: vi.fn().mockResolvedValue(undefined),
  cachePlaceId: vi.fn().mockResolvedValue(undefined),
  getCachedLatLng: vi.fn().mockResolvedValue(null),
  getCachedPlaceId: vi.fn().mockResolvedValue(null),
}));

let upstashCache: ReturnType<typeof buildUpstashCacheMock>;
vi.mock("@/lib/cache/upstash", () => {
  upstashCache = buildUpstashCacheMock();
  return upstashCache.module;
});
vi.mock("@/lib/cache/tags", () => ({
  bumpTag: vi.fn(async () => 1),
  versionedKey: vi.fn(async (_tag: string, key: string) => `tag:v1:${key}`),
}));

import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { AccommodationsService } from "@domain/accommodations/service";
import { getCachedJson } from "@/lib/cache/upstash";
import { getCachedLatLng } from "@/lib/google/caching";

describe("AccommodationsService (Amadeus)", () => {
  beforeEach(() => {
    server.use(
      http.post("https://places.googleapis.com/v1/places:searchText", () =>
        HttpResponse.json({
          places: [
            { id: "places/abc", location: { latitude: 1.234, longitude: 2.345 } },
          ],
        })
      )
    );
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
    const searchMock = provider.search as unknown as ReturnType<typeof vi.fn>;
    const [searchCallArgs] = searchMock.mock.calls[0] ?? [];
    expect(searchCallArgs?.lat).toBeCloseTo(1.234);
    expect(searchCallArgs?.lng).toBeCloseTo(2.345);
  });

  it("keeps listings when cheaper rates are not first", async () => {
    vi.mocked(getCachedLatLng).mockResolvedValue({ lat: 1, lon: 1 });
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
                    { price: { currency: "USD", numeric: 400, total: "400.00" } },
                  ],
                },
                {
                  rates: [
                    { price: { currency: "USD", numeric: 150, total: "150.00" } },
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

    const result = await service.search(
      {
        checkin: "2025-12-01",
        checkout: "2025-12-02",
        guests: 1,
        location: "Paris",
        priceMax: 200,
      },
      {
        sessionId: "sess-1",
      }
    );

    expect(result.resultsReturned).toBe(1);
  });

  it("propagates a deterministic sessionId derived from userId when missing", async () => {
    vi.mocked(getCachedLatLng).mockResolvedValue({ lat: 1, lon: 1 });
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn(),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn().mockResolvedValue({
        ok: true,
        retries: 0,
        value: { currency: "USD", listings: [], total: 0 },
      }),
    };

    const service = new AccommodationsService({
      cacheTtlSeconds: 0,
      provider,
      rateLimiter: undefined,
      supabase: async () =>
        ({}) as unknown as import("@/lib/supabase/server").TypedServerSupabase,
    });

    await service.search(
      {
        checkin: "2025-12-01",
        checkout: "2025-12-02",
        guests: 1,
        location: "Paris",
      },
      {
        rateLimitKey: "ip:1.1.1.1",
        userId: "user-123",
      }
    );

    const searchMock = provider.search as unknown as ReturnType<typeof vi.fn>;
    const [, providerCtx] = searchMock.mock.calls[0] ?? [];
    expect(providerCtx?.sessionId).toBe("user-123");
    expect(providerCtx?.userId).toBe("user-123");
  });

  it("enriches details with Google Places when available", async () => {
    let callCount = 0;
    server.use(
      http.post("https://places.googleapis.com/v1/places:searchText", () => {
        callCount++;
        if (callCount === 1) {
          return HttpResponse.json({
            places: [{ id: "places/test", location: { latitude: 0, longitude: 0 } }],
          });
        }
        return HttpResponse.json({
          id: "places/test",
          rating: 4.5,
          userRatingCount: 123,
        });
      })
    );

    // Cache misses; force live fetch to ensure enrichment path populates rating
    vi.mocked(getCachedJson).mockResolvedValue(null);

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

    const listing = details.listing as {
      hotel?: { address?: { cityName?: string }; name?: string };
      place?: { id?: string; rating?: number };
    };

    expect(listing.hotel).toMatchObject({
      address: { cityName: "Paris" },
      name: "Test Hotel",
    });
    expect(listing.place).toMatchObject({
      id: "places/test",
    });
  });
});
