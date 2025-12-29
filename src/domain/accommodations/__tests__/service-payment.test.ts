/** @vitest-environment node */

import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

type AccommodationsServiceDeps =
  import("@domain/accommodations/service").AccommodationsServiceDeps;
type TypedServerSupabase = import("@/lib/supabase/server").TypedServerSupabase;

vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: vi.fn(),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    async <T>(
      _name: string,
      _options: unknown,
      fn: (span: {
        addEvent: (name: string, attrs?: Record<string, unknown>) => void;
        recordException: (error: unknown) => void;
      }) => T | Promise<T>
    ): Promise<T> =>
      await fn({
        addEvent: vi.fn(),
        recordException: vi.fn(),
      })
  ),
}));

const { AccommodationsService } = await import("@domain/accommodations/service");

describe("AccommodationsService booking payments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses cached availability price for payment processing", async () => {
    const bookingPrice = {
      bookingToken: "token-123",
      price: { currency: "USD", total: "123.45" },
      propertyId: "H1",
      rateId: "token-123",
      userId: "user-1",
    };

    const processPayment = vi.fn().mockResolvedValue({ paymentIntentId: "pi_test" });
    const providerPayload = { data: { sample: true } };
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(() => providerPayload),
      checkAvailability: vi.fn(),
      createBooking: vi.fn().mockResolvedValue({
        ok: true,
        retries: 0,
        value: { providerBookingId: "bk1" },
      }),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn(),
    };

    const supabase = unsafeCast<TypedServerSupabase>({
      from: (table: string) => {
        if (table === "trips") {
          return {
            select: () => ({
              eq: () => ({
                eq: () => ({
                  single: async () => ({
                    data: { id: 1, user_id: "user-1" },
                    error: null,
                  }),
                }),
              }),
            }),
          };
        }
        if (table === "bookings") {
          return {
            insert: async () => ({ error: null }),
          };
        }
        return unsafeCast<Record<string, unknown>>({});
      },
    });

    let getKey: string | undefined;
    const getCachedJson: AccommodationsServiceDeps["getCachedJson"] = <T>(
      key: string
    ): Promise<T | null> => {
      getKey = key;
      return Promise.resolve(unsafeCast<T>(bookingPrice));
    };

    const bumpTag = vi.fn(async () => 1);

    const service = new AccommodationsService({
      bumpTag,
      cacheTtlSeconds: 0,
      canonicalizeParamsForCache: (params, prefix) =>
        `${prefix}:${JSON.stringify(params)}`,
      enrichHotelListingWithPlaces: async (listing) => listing,
      getCachedJson,
      provider,
      resolveLocationToLatLng: async (_location) => ({ lat: 1, lon: 1 }),
      retryWithBackoff: async (fn, _options) => await fn(0),
      setCachedJson: async () => undefined,
      supabase: async () => supabase,
      versionedKey: async (_tag: string, key: string) => `tag:v1:${key}`,
    });

    await service.book(
      {
        amount: 1000,
        bookingToken: "token-123",
        checkin: "2025-12-01",
        checkout: "2025-12-02",
        currency: "USD",
        guestEmail: "guest@example.com",
        guestName: "Test User",
        guestPhone: "+123",
        guests: 1,
        listingId: "H1",
        paymentMethodId: "pm_test",
        sessionId: "session",
        specialRequests: "",
        tripId: "1",
      },
      {
        processPayment: ({ amountCents }) =>
          processPayment({ amountCents, currency: "USD" }),
        requestApproval: vi.fn().mockResolvedValue(undefined),
        sessionId: "session",
        userId: "user-1",
      }
    );

    expect(getKey).toContain("token-123");
    expect(processPayment).toHaveBeenCalledWith({
      amountCents: 12345,
      currency: "USD",
    });
    expect(bumpTag).toHaveBeenCalledWith("accommodations:search");

    expect(provider.buildBookingPayload).toHaveBeenCalledWith(
      expect.objectContaining({ bookingToken: "token-123" }),
      {
        currency: "USD",
        paymentIntentId: "pi_test",
        totalCents: 12345,
      }
    );

    expect(provider.createBooking).toHaveBeenCalledWith(providerPayload, {
      sessionId: "session",
      userId: "user-1",
    });
  });
});
