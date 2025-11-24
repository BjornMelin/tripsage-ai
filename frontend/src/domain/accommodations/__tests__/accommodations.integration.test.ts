/** @vitest-environment node */

import { AmadeusProviderAdapter } from "@domain/accommodations/providers/amadeus-adapter";
import { AccommodationsService } from "@domain/accommodations/service";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { googlePlacesHandlers } from "@/test/msw/handlers/google-places";
import { stripeHandlers } from "@/test/msw/handlers/stripe";
import { composeHandlers } from "@/test/msw/handlers/utils";
import { server } from "@/test/msw/server";

const cache = new Map<string, unknown>();

vi.mock("@/lib/cache/upstash", () => ({
  deleteCachedJson: vi.fn((key: string) => {
    cache.delete(key);
    return Promise.resolve();
  }),
  getCachedJson: vi.fn((key: string) =>
    Promise.resolve(cache.has(key) ? cache.get(key) : null)
  ),
  setCachedJson: vi.fn((key: string, value: unknown) => {
    cache.set(key, value);
  }),
}));

vi.mock("@/lib/google/caching", () => ({
  cacheLatLng: vi.fn(),
  cachePlaceId: vi.fn(),
  getCachedLatLng: vi.fn().mockResolvedValue(null),
  getCachedPlaceId: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/lib/env/server", async (orig) => {
  const actual = (await orig()) as Record<string, unknown>;
  return {
    ...actual,
    getGoogleMapsServerKey: () => "test-google-key",
  };
});

vi.mock("@domain/amadeus/client", () => ({
  bookHotelOffer: async () => ({
    data: { id: "BOOK-1", providerConfirmationId: "CONF-123" },
  }),
  listHotelsByGeocode: async () => ({
    data: [
      {
        address: { cityName: "Paris", lines: ["123 Mock St"] },
        geoCode: { latitude: 48.8566, longitude: 2.3522 },
        hotelId: "H1",
        name: "Mock Hotel",
      },
    ],
  }),
  searchHotelOffers: async () => ({
    data: [
      {
        hotel: {
          address: { cityName: "Paris", lines: ["123 Mock St"] },
          geoCode: { latitude: 48.8566, longitude: 2.3522 },
          hotelId: "H1",
          name: "Mock Hotel",
        },
        offers: [
          {
            checkInDate: "2025-12-01",
            checkOutDate: "2025-12-03",
            id: "OFFER-1",
            policies: { refundable: true },
            price: { base: "189.00", currency: "USD", total: "199.00" },
            room: {
              description: { text: "Queen Room" },
              typeEstimated: { bedType: "Queen", category: "STANDARD_ROOM" },
            },
          },
        ],
      },
    ],
  }),
}));

const handlerSet = composeHandlers(googlePlacesHandlers, stripeHandlers);

beforeEach(async () => {
  cache.clear();
  const cachingModule = await import("@/lib/google/caching");
  const getCachedLatLng = vi.mocked(cachingModule.getCachedLatLng);
  getCachedLatLng.mockResolvedValue({ lat: 48.8566, lon: 2.3522 });
  server.use(...handlerSet);
});

afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

const createService = (supabaseInserts: unknown[]) =>
  new AccommodationsService({
    cacheTtlSeconds: 60,
    provider: new AmadeusProviderAdapter(),
    rateLimiter: undefined,
    supabase: async () =>
      ({
        from: () => ({
          insert: (payload: unknown) => {
            supabaseInserts.push(payload);
            return Promise.resolve({ error: null });
          },
          select: () => ({
            eq: () => ({
              eq: () => ({
                single: async () => ({
                  data: { id: 11, user_id: "user-1" },
                  error: null,
                }),
              }),
            }),
          }),
        }),
      }) as unknown as import("@/lib/supabase/server").TypedServerSupabase,
  });

describe("AccommodationsService end-to-end (Amadeus + Places + Stripe mocks)", () => {
  it("searches and caches results", async () => {
    const service = createService([]);

    const search = await service.search({
      checkin: "2025-12-01",
      checkout: "2025-12-03",
      guests: 2,
      location: "Paris",
    });

    expect(search.listings).toHaveLength(1);
    const searchListing = search.listings[0] as {
      rooms?: Array<{ rates?: Array<{ price?: { total?: string } }> }>;
    };
    expect(searchListing.rooms?.[0]?.rates?.[0]?.price?.total).toBe("199.00");
    expect(cache.size).toBeGreaterThan(0);
  });

  it("returns enriched details with place rating", async () => {
    const service = createService([]);

    const details = await service.details({
      listingId: "H1",
    });
    const listing = details.listing as { placeDetails?: { rating?: number } };
    expect(listing.placeDetails?.rating).toBe(4.5);
  });

  it("checks availability and returns booking token", async () => {
    const service = createService([]);

    const availability = await service.checkAvailability(
      {
        checkIn: "2025-12-01",
        checkOut: "2025-12-03",
        guests: 2,
        priceCheckToken: "price-1",
        propertyId: "H1",
        rateId: "OFFER-1",
        roomId: "ROOM-1",
      },
      { sessionId: "sess-1", userId: "user-1" }
    );

    expect(availability.price.total).toBe("199.00");
    expect(availability.bookingToken).toBe("OFFER-1");
  });

  it("books and persists payment + confirmation", async () => {
    const supabaseInserts: unknown[] = [];
    const service = createService(supabaseInserts);

    const availability = await service.checkAvailability(
      {
        checkIn: "2025-12-01",
        checkOut: "2025-12-03",
        guests: 2,
        priceCheckToken: "price-1",
        propertyId: "H1",
        rateId: "OFFER-1",
        roomId: "ROOM-1",
      },
      { sessionId: "sess-1", userId: "user-1" }
    );

    const booking = await service.book(
      {
        amount: 19900,
        bookingToken: availability.bookingToken,
        checkin: "2025-12-01",
        checkout: "2025-12-03",
        currency: "USD",
        guestEmail: "ada@example.com",
        guestName: "Ada Lovelace",
        guests: 2,
        listingId: "H1",
        paymentMethodId: "pm_mock",
        sessionId: "sess-1",
        specialRequests: "Late arrival",
        tripId: "11",
      },
      {
        processPayment: async ({ amountCents, currency }) => {
          const res = await fetch("https://api.stripe.com/v1/payment_intents", {
            body: JSON.stringify({ amount: amountCents, currency }),
            method: "POST",
          });
          const json = await res.json();
          return { paymentIntentId: json.id };
        },
        requestApproval: vi.fn(),
        sessionId: "sess-1",
        userId: "user-1",
      }
    );

    expect(booking.providerBookingId).toBe("BOOK-1");
    expect(supabaseInserts[0]).toMatchObject({
      provider_booking_id: "BOOK-1",
      stripe_payment_intent_id: "pi_mock",
    });
  });
});
