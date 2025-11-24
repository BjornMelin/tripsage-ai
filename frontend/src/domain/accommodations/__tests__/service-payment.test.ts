/** @vitest-environment node */

import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { AccommodationsService } from "@domain/accommodations/service";
import { describe, expect, it, vi } from "vitest";
import { getCachedJson } from "@/lib/cache/upstash";
import type { buildUpstashCacheMock } from "@/test/mocks";

const getUpstashCache = (): ReturnType<typeof buildUpstashCacheMock> =>
  (globalThis as { __upstashCache?: ReturnType<typeof buildUpstashCacheMock> })
    .__upstashCache as ReturnType<typeof buildUpstashCacheMock>;

vi.mock("@/lib/cache/upstash", async () => {
  const { buildUpstashCacheMock } = await import("@/test/mocks");
  const cache = buildUpstashCacheMock();
  (
    globalThis as { __upstashCache?: ReturnType<typeof buildUpstashCacheMock> }
  ).__upstashCache = cache;
  return cache.module;
});

vi.mock("@/lib/google/caching", () => ({
  cacheLatLng: vi.fn(),
  getCachedLatLng: vi.fn(),
}));

describe("AccommodationsService booking payments", () => {
  beforeEach(() => {
    getUpstashCache().reset();
  });

  it("uses cached availability price for payment processing", async () => {
    vi.mocked(getCachedJson).mockResolvedValue({
      bookingToken: "token-123",
      price: { currency: "USD", total: "123.45" },
      propertyId: "H1",
      rateId: "token-123",
      userId: "user-1",
    });
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

    const supabase = {
      from: (table: string) => ({
        insert: async () => ({ error: null }),
        select: () => ({
          eq: () => ({
            eq: () => ({
              single: async () =>
                table === "trips"
                  ? { data: { id: 1, user_id: "user-1" }, error: null }
                  : { data: null, error: null },
            }),
          }),
        }),
      }),
    };

    const service = new AccommodationsService({
      cacheTtlSeconds: 0,
      provider,
      rateLimiter: undefined,
      supabase: async () =>
        supabase as unknown as import("@/lib/supabase/server").TypedServerSupabase,
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

    expect(processPayment).toHaveBeenCalledWith({
      amountCents: 12345,
      currency: "USD",
    });

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
