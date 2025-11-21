import { AmadeusProviderAdapter } from "@domain/accommodations/providers/amadeus-adapter";
import { AccommodationsService } from "@domain/accommodations/service";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

const cache = new Map<string, unknown>();

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn(async (key: string) => (cache.has(key) ? cache.get(key) : null)),
  setCachedJson: vi.fn((key: string, value: unknown) => {
    cache.set(key, value);
  }),
}));

vi.mock("@/lib/google/caching", () => ({
  cacheLatLng: vi.fn(),
  getCachedLatLng: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/lib/env/server", async (orig) => {
  const actual = (await orig()) as Record<string, unknown>;
  return {
    ...actual,
    getGoogleMapsServerKey: () => "test-google-key",
  };
});

vi.mock("@domain/amadeus/client", () => ({
  bookHotelOffer: async (payload: unknown) => {
    const res = await fetch("https://test.api.amadeus.com/v1/booking/hotel-bookings", {
      body: JSON.stringify(payload),
      method: "POST",
    });
    return { data: await res.json() };
  },
  listHotelsByGeocode: async () => {
    const res = await fetch(
      "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode"
    );
    return { data: await res.json() };
  },
  searchHotelOffers: async () => {
    const res = await fetch("https://test.api.amadeus.com/v3/shopping/hotel-offers");
    const json = await res.json();
    return { data: json.data };
  },
}));

const server = setupServer(
  // Google Places geocode
  http.post("https://places.googleapis.com/v1/places:searchText", async () =>
    HttpResponse.json({
      places: [
        {
          id: "places/mock-place",
          location: { latitude: 48.8566, longitude: 2.3522 },
        },
      ],
    })
  ),
  // Google Places details
  http.get("https://places.googleapis.com/v1/places/mock-place", async () =>
    HttpResponse.json({
      displayName: { text: "Mock Place" },
      formattedAddress: "123 Mock St, Paris",
      id: "places/mock-place",
      photos: [{ name: "photo/mock" }],
      rating: 4.7,
      userRatingCount: 120,
    })
  ),
  // Amadeus hotel geocode search
  http.get(
    "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode",
    async () =>
      HttpResponse.json([
        {
          address: { cityName: "Paris", lines: ["123 Mock St"] },
          geoCode: { latitude: 48.8566, longitude: 2.3522 },
          hotelId: "H1",
          name: "Mock Hotel",
        },
      ])
  ),
  // Amadeus offers search
  http.get("https://test.api.amadeus.com/v3/shopping/hotel-offers", async () =>
    HttpResponse.json({
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
    })
  ),
  // Amadeus booking
  http.post("https://test.api.amadeus.com/v1/booking/hotel-bookings", async () =>
    HttpResponse.json({ id: "BOOK-1", providerConfirmationId: "CONF-123" })
  ),
  // Stripe PaymentIntent
  http.post("https://api.stripe.com/v1/payment_intents", async () =>
    HttpResponse.json({ id: "pi_mock", status: "succeeded" })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("AccommodationsService end-to-end (Amadeus + Places + Stripe mocks)", () => {
  it("searches, enriches, checks availability, and books", async () => {
    const supabaseInserts: unknown[] = [];
    const service = new AccommodationsService({
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
                  single: async () => ({ data: { id: 11, user_id: "user-1" }, error: null }),
                }),
              }),
            }),
          }),
        }) as unknown as import("@/lib/supabase/server").TypedServerSupabase,
    });

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

    const details = await service.details({
      listingId: "H1",
    });
    const listing = details.listing as { placeDetails?: { rating?: number } };
    expect(listing.placeDetails?.rating).toBe(4.7);

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
