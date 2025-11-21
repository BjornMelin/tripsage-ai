import { runBookingOrchestrator } from "@domain/accommodations/booking-orchestrator";
import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/payments/booking-payment", () => ({
  refundBookingPayment: vi.fn().mockResolvedValue(undefined),
}));

describe("runBookingOrchestrator", () => {
  it("processes booking and persists provider booking id", async () => {
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn().mockResolvedValue({
        ok: true,
        retries: 0,
        value: {
          confirmationNumber: "CONF123",
          itineraryId: "ITIN123",
          providerBookingId: "PB123",
        },
      }),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn(),
    };

    const supabase = {
      from: () => ({
        insert: async () => ({ error: null }),
      }),
    } as any;

    const result = await runBookingOrchestrator(
      { provider, supabase },
      {
        amount: 10000,
        approvalKey: "bookAccommodation",
        bookingToken: "token",
        currency: "USD",
        guest: { email: "test@example.com", name: "Test User" },
        idempotencyKey: "idem",
        paymentMethodId: "pm_123",
        persistBooking: vi.fn().mockResolvedValue(undefined),
        processPayment: async () => ({ paymentIntentId: "pi_123" }) as any,
        providerPayload: {},
        requestApproval: vi.fn().mockResolvedValue(undefined),
        sessionId: "sess",
        stay: {
          checkin: "2025-12-01",
          checkout: "2025-12-02",
          guests: 1,
          listingId: "H1",
        },
        userId: "user-1",
      }
    );

    expect(result.epsBookingId).toBe("ITIN123");
    expect(result.reference).toContain("CONF");
  });
});
