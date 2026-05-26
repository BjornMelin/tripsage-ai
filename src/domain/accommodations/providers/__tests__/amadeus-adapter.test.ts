/** @vitest-environment node */

import type { ProviderError } from "@domain/accommodations/errors";
import {
  AmadeusProviderAdapter,
  mapStatusToProviderCode,
} from "@domain/accommodations/providers/amadeus-adapter";
import { beforeEach, vi } from "vitest";
import { withFakeTimers } from "@/test/utils/with-fake-timers";

vi.mock("@domain/amadeus/client", () => ({
  bookHotelOffer: vi.fn(),
  listHotelsByGeocode: vi.fn(),
  searchHotelOffers: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AmadeusProviderAdapter.buildBookingPayload", () => {
  it("maps Stripe PaymentIntent into Amadeus payments payload", () => {
    const adapter = new AmadeusProviderAdapter();

    const payload = adapter.buildBookingPayload(
      {
        amount: 45678,
        bookingToken: "OFFER-1",
        checkin: "2025-12-01",
        checkout: "2025-12-05",
        currency: "USD",
        guestEmail: "ada@example.com",
        guestName: "Ada Lovelace",
        guestPhone: "+12065550123",
        guests: 2,
        listingId: "H123",
        paymentMethodId: "pm_123",
        sessionId: "session-1",
        specialRequests: "Late check-in",
        tripId: "42",
      },
      {
        currency: "USD",
        paymentIntentId: "pi_abc123",
        title: "MR",
        totalCents: 45678,
      }
    );

    const data = payload.data as {
      guests: Array<{
        name: { firstName?: string; lastName?: string; title?: string };
      }>;
      hotelOffers: Array<{ id: string }>;
      payments?: Array<{
        amount: { amount: string; currencyCode: string };
        method: string;
        reference: string;
        vendorCode: string;
      }>;
      remarks?: { general?: Array<{ text?: string }> };
    };

    expect(data.hotelOffers).toEqual([{ id: "OFFER-1" }]);
    expect(data.payments?.[0]).toEqual({
      amount: { amount: "456.78", currencyCode: "USD" },
      method: "external_prepaid",
      reference: "pi_abc123",
      vendorCode: "STRIPE",
    });
    expect(data.guests[0].name).toEqual({
      firstName: "Ada",
      lastName: "Lovelace",
      title: "MR",
    });
    expect(data.remarks?.general?.[0]?.text).toContain("StripePaymentIntent=pi_abc123");
  });
});

describe("AmadeusProviderAdapter.getDetails", () => {
  it(
    "defaults missing details dates to current and next UTC ISO dates",
    withFakeTimers(async () => {
      vi.setSystemTime(new Date("2025-12-31T23:30:00Z"));

      const adapter = new AmadeusProviderAdapter();
      const { searchHotelOffers } = await import("@domain/amadeus/client");
      vi.mocked(searchHotelOffers).mockResolvedValue({ data: [] } as never);

      const result = await adapter.getDetails(
        { listingId: "H123" },
        { sessionId: "sess-1", userId: "user-1" }
      );

      expect(result.ok).toBe(true);
      expect(searchHotelOffers).toHaveBeenCalledWith({
        adults: 1,
        checkInDate: "2025-12-31",
        checkOutDate: "2026-01-01",
        hotelIds: ["H123"],
      });
    })
  );
});

describe("AmadeusProviderAdapter.checkAvailability", () => {
  it(
    "sets availability token expiry from the current timestamp helper",
    withFakeTimers(async () => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));

      const adapter = new AmadeusProviderAdapter();
      const { searchHotelOffers } = await import("@domain/amadeus/client");
      vi.mocked(searchHotelOffers).mockResolvedValue({
        data: [
          {
            hotel: { hotelId: "H123", name: "Hotel Example" },
            offers: [
              {
                checkInDate: "2026-02-10",
                checkOutDate: "2026-02-12",
                id: "RATE-1",
                price: {
                  base: "100.00",
                  currency: "USD",
                  total: "118.40",
                },
              },
            ],
          },
        ],
      } as never);

      const result = await adapter.checkAvailability(
        {
          checkIn: "2026-02-10",
          checkOut: "2026-02-12",
          guests: 2,
          priceCheckToken: "RATE-1",
          propertyId: "H123",
          rateId: "RATE-1",
          roomId: "ROOM-1",
        },
        { sessionId: "sess-1", userId: "user-1" }
      );

      expect(result).toEqual({
        ok: true,
        retries: 0,
        value: {
          bookingToken: "RATE-1",
          expiresAt: "2026-02-03T04:15:06.000Z",
          price: {
            breakdown: {
              base: "100.00",
            },
            currency: "USD",
            total: "118.40",
          },
          propertyId: "H123",
          rateId: "RATE-1",
        },
      });
    })
  );
});

describe("AmadeusProviderAdapter error normalization", () => {
  it("maps Amadeus HTTP status codes to ProviderError codes", () => {
    const cases: Array<{ statusCode: number; expected: ProviderError["code"] }> = [
      { expected: "provider_timeout", statusCode: 408 },
      { expected: "unauthorized", statusCode: 401 },
      { expected: "not_found", statusCode: 404 },
      { expected: "rate_limited", statusCode: 429 },
      { expected: "provider_failed", statusCode: 500 },
    ];

    for (const testCase of cases) {
      expect(mapStatusToProviderCode(testCase.statusCode)).toBe(testCase.expected);
    }
  });

  it("returns provider_timeout when an operation exceeds the deadline", async () => {
    vi.useFakeTimers();
    try {
      const adapter = new AmadeusProviderAdapter();

      const { listHotelsByGeocode, searchHotelOffers } = await import(
        "@domain/amadeus/client"
      );
      // Create a pending promise that never resolves (for timeout testing)
      const pending = new Promise<never>(() => {
        // Intentionally empty - promise never resolves
      });
      vi.mocked(listHotelsByGeocode).mockReturnValue(pending as never);
      vi.mocked(searchHotelOffers).mockResolvedValue({ data: [] } as never);

      const resultPromise = adapter.search(
        {
          checkin: "2025-12-01",
          checkout: "2025-12-02",
          guests: 1,
          lat: 1,
          lng: 1,
          location: "Paris",
        },
        { sessionId: "sess-123", userId: "user-123" }
      );

      await vi.runAllTimersAsync();
      const result = await resultPromise;

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("provider_timeout");
        expect(result.error.statusCode).toBe(408);
      }
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not retry createBooking on timeout (non-idempotent)", async () => {
    vi.useFakeTimers();
    try {
      const adapter = new AmadeusProviderAdapter();
      const { bookHotelOffer } = await import("@domain/amadeus/client");
      // Create a pending promise that never resolves (for timeout testing)
      const pending = new Promise<never>(() => {
        // Intentionally empty - promise never resolves
      });
      vi.mocked(bookHotelOffer).mockReturnValue(pending as never);

      const resultPromise = adapter.createBooking(
        { data: { hotelOffers: [{ id: "OFFER-1" }], type: "hotel-order" } },
        { sessionId: "sess-1", userId: "user-1" }
      );

      await vi.runAllTimersAsync();
      const result = await resultPromise;

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("provider_timeout");
      }
      expect(vi.mocked(bookHotelOffer)).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("honors custom timeout configuration", async () => {
    vi.useFakeTimers();
    try {
      const adapter = new AmadeusProviderAdapter({ timeoutMs: 5 });
      const { listHotelsByGeocode } = await import("@domain/amadeus/client");
      // Create a pending promise that never resolves (for timeout testing)
      vi.mocked(listHotelsByGeocode).mockReturnValue(
        new Promise<never>(() => {
          // Intentionally empty - promise never resolves
        }) as never
      );

      const resultPromise = adapter.search(
        {
          checkin: "2025-12-01",
          checkout: "2025-12-02",
          guests: 1,
          lat: 1,
          lng: 1,
          location: "Paris",
        },
        { sessionId: "sess-123", userId: "user-123" }
      );

      await vi.runAllTimersAsync();
      const result = await resultPromise;

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("provider_timeout");
      }
    } finally {
      vi.useRealTimers();
    }
  });

  it(
    "clears timeout when the provider operation throws synchronously",
    withFakeTimers(async () => {
      const adapter = new AmadeusProviderAdapter({ timeoutMs: 1_000 });
      const { listHotelsByGeocode, searchHotelOffers } = await import(
        "@domain/amadeus/client"
      );
      vi.mocked(listHotelsByGeocode).mockImplementation(() => {
        throw new Error("sync provider failure");
      });
      vi.mocked(searchHotelOffers).mockResolvedValue({ data: [] } as never);

      const result = await adapter.search(
        {
          checkin: "2025-12-01",
          checkout: "2025-12-02",
          guests: 1,
          lat: 1,
          lng: 1,
          location: "Paris",
        },
        { sessionId: "sess-123", userId: "user-123" }
      );

      expect(result.ok).toBe(false);
      expect(vi.getTimerCount()).toBe(0);
    })
  );
});
