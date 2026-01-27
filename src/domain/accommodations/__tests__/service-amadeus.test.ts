/** @vitest-environment node */

import { ProviderError } from "@domain/accommodations/errors";
import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { accommodationSearchOutputSchema } from "@schemas/accommodations";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

type AccommodationsServiceDeps =
  import("@domain/accommodations/service").AccommodationsServiceDeps;

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: async (
    _name: string,
    _options: unknown,
    fn: (span: {
      addEvent: (name: string, attributes?: Record<string, unknown>) => void;
      recordException: (error: unknown) => void;
    }) => Promise<unknown>
  ) => await fn({ addEvent: vi.fn(), recordException: vi.fn() }),
}));

const { withTelemetrySpan } = await import("@/lib/telemetry/span");
const { AccommodationsService } = await import("@domain/accommodations/service");

const CACHE_NAMESPACE = "service:accom:search";
const CACHE_TAG_SEARCH = "accommodations:search";

function createService(options: {
  coords?: { lat: number; lon: number } | null;
  enrich?: AccommodationsServiceDeps["enrichHotelListingWithPlaces"];
  provider: AccommodationProviderAdapter;
}) {
  const cache = new Map<string, unknown>();

  const defaultEnrich: AccommodationsServiceDeps["enrichHotelListingWithPlaces"] =
    async (listing) => listing;

  const getCachedJson: AccommodationsServiceDeps["getCachedJson"] = <T>(
    key: string
  ): Promise<T | null> => {
    if (!cache.has(key)) return Promise.resolve(null);
    return Promise.resolve(unsafeCast<T>(cache.get(key)));
  };

  const setCachedJson: AccommodationsServiceDeps["setCachedJson"] = (key, value) => {
    cache.set(key, value);
    return Promise.resolve();
  };

  const deps: AccommodationsServiceDeps = {
    bumpTag: vi.fn(async () => 1),
    cacheTtlSeconds: 0,
    canonicalizeParamsForCache: (params, prefix) =>
      `${prefix}:${JSON.stringify(params)}`,
    enrichHotelListingWithPlaces: options.enrich ?? defaultEnrich,
    getCachedJson,
    getTripOwnership: vi.fn(async () => null),
    persistBooking: vi.fn(async () => ({ error: null })),
    provider: options.provider,
    resolveLocationToLatLng: () =>
      Promise.resolve(
        options.coords === undefined ? { lat: 1.234, lon: 2.345 } : options.coords
      ),
    retryWithBackoff: (fn) => fn(0),
    setCachedJson,
    versionedKey: async (_tag, key) => `tag:v1:${key}`,
    withTelemetrySpan,
  };

  return { cache, deps, service: new AccommodationsService(deps) };
}

describe("AccommodationsService (Amadeus)", () => {
  beforeEach(() => {
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

    const { service } = createService({
      coords: { lat: 1.234, lon: 2.345 },
      provider,
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
    const searchMock = vi.mocked(provider.search);
    const [searchCallArgs] = searchMock.mock.calls[0] ?? [];
    expect(searchCallArgs?.lat).toBeCloseTo(1.234);
    expect(searchCallArgs?.lng).toBeCloseTo(2.345);
  });

  it("keeps listings when cheaper rates are not first", async () => {
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

    const { service } = createService({ provider });

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

    const { service } = createService({ provider });

    await service.search(
      {
        checkin: "2025-12-01",
        checkout: "2025-12-02",
        guests: 1,
        location: "Paris",
      },
      {
        userId: "user-123",
      }
    );

    const searchMock = vi.mocked(provider.search);
    const [, providerCtx] = searchMock.mock.calls[0] ?? [];
    expect(providerCtx?.sessionId).toBe("user-123");
    expect(providerCtx?.userId).toBe("user-123");
  });

  it("returns cached results without calling provider", async () => {
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn(),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn(),
    };

    const { cache, deps, service } = createService({ provider });
    const params = {
      checkin: "2025-12-01",
      checkout: "2025-12-02",
      guests: 1,
      location: "Paris",
    };
    const baseCacheKey = deps.canonicalizeParamsForCache(
      { ...params, semanticQuery: "" },
      CACHE_NAMESPACE
    );
    const versionedKey = await deps.versionedKey(CACHE_TAG_SEARCH, baseCacheKey);
    cache.set(
      versionedKey,
      accommodationSearchOutputSchema.parse({
        fromCache: false,
        listings: [],
        provider: "amadeus",
        resultsReturned: 0,
        searchId: "search-1",
        searchParameters: {},
        status: "success",
        tookMs: 1,
        totalResults: 0,
      })
    );

    const result = await service.search(params);

    expect(result.fromCache).toBe(true);
    expect(provider.search).not.toHaveBeenCalled();
  });

  it("enriches details output when enrichment adapter returns place data", async () => {
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

    const { service } = createService({
      enrich: async (listing) => ({
        ...listing,
        place: { id: "places/test" },
      }),
      provider,
    });

    const details = await service.details({ listingId: "H1" });
    expect(details.provider).toBe("amadeus");
    expect(details.status).toBe("success");
    expect(unsafeCast<{ place?: { id?: string } }>(details.listing).place?.id).toBe(
      "places/test"
    );
  });

  it("throws a not_found ProviderError when geocoding fails", async () => {
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn(),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn(),
    };

    const { service } = createService({ coords: null, provider });

    await expect(
      service.search({
        checkin: "2025-12-01",
        checkout: "2025-12-02",
        guests: 1,
        location: "Paris",
      })
    ).rejects.toBeInstanceOf(ProviderError);
  });
});
