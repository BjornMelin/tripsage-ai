/** @vitest-environment node */

import { runBookingOrchestrator } from "@domain/accommodations/booking-orchestrator";
import { ProviderError } from "@domain/accommodations/errors";
import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { vi } from "vitest";

vi.mock("@/lib/payments/booking-payment", () => ({
  refundBookingPayment: vi.fn().mockResolvedValue({ amount: 0, refundId: "rf_1" }),
}));

import { refundBookingPayment } from "@/lib/payments/booking-payment";

const baseCommand = {
  amount: 10000,
  approvalKey: "bookAccommodation",
  bookingToken: "tok_1",
  currency: "USD",
  guest: { email: "ada@example.com", name: "Ada" },
  idempotencyKey: "idem-1",
  paymentMethodId: "pm_1",
  providerPayload: {},
  requestApproval: vi.fn(),
  sessionId: "sess-1",
  stay: {
    checkin: "2025-12-01",
    checkout: "2025-12-03",
    guests: 2,
    listingId: "H1",
    tripId: "42",
  },
  userId: "user-1",
};

describe("runBookingOrchestrator", () => {
  it("refunds payment when provider booking fails", async () => {
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn().mockResolvedValue({
        error: new ProviderError("provider_failed", "failed"),
        ok: false,
        retries: 0,
      }),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn(),
    };

    const supabase = {
      from: vi
        .fn()
        .mockReturnValue({ insert: vi.fn().mockResolvedValue({ error: null }) }),
    } as unknown as import("@/lib/supabase/server").TypedServerSupabase;

    await expect(
      runBookingOrchestrator(
        { provider, supabase },
        {
          ...baseCommand,
          persistBooking: vi.fn(),
          processPayment: vi.fn().mockResolvedValue({ paymentIntentId: "pi_fail" }),
        }
      )
    ).rejects.toBeInstanceOf(ProviderError);

    expect(refundBookingPayment).toHaveBeenCalledWith("pi_fail");
  });

  it("persists provider booking ids on success", async () => {
    const persistBooking = vi.fn().mockResolvedValue(undefined);
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn().mockResolvedValue({
        ok: true,
        retries: 0,
        value: {
          confirmationNumber: "CONF-1",
          providerBookingId: "PB-1",
        },
      }),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn(),
    };

    const supabase = {
      from: vi
        .fn()
        .mockReturnValue({ insert: vi.fn().mockResolvedValue({ error: null }) }),
    } as unknown as import("@/lib/supabase/server").TypedServerSupabase;

    await runBookingOrchestrator(
      { provider, supabase },
      {
        ...baseCommand,
        persistBooking,
        processPayment: vi.fn().mockResolvedValue({ paymentIntentId: "pi_success" }),
      }
    );

    expect(persistBooking).toHaveBeenCalledTimes(1);
    expect(persistBooking.mock.calls[0][0]).toMatchObject({
      confirmationNumber: "CONF-1",
      providerBookingId: "PB-1",
      stripePaymentIntentId: "pi_success",
    });
  });

  it("refunds payment if persistence fails after provider booking success", async () => {
    const persistBooking = vi.fn().mockRejectedValue(new Error("db down"));
    const provider: AccommodationProviderAdapter = {
      buildBookingPayload: vi.fn(),
      checkAvailability: vi.fn(),
      createBooking: vi.fn().mockResolvedValue({
        ok: true,
        retries: 0,
        value: {
          confirmationNumber: "CONF-2",
          providerBookingId: "PB-2",
        },
      }),
      getDetails: vi.fn(),
      name: "amadeus",
      search: vi.fn(),
    };

    const supabase = {
      from: vi.fn().mockReturnValue({
        insert: vi.fn().mockResolvedValue({ error: null }),
      }),
    } as unknown as import("@/lib/supabase/server").TypedServerSupabase;

    await expect(
      runBookingOrchestrator(
        { provider, supabase },
        {
          ...baseCommand,
          persistBooking,
          processPayment: vi.fn().mockResolvedValue({ paymentIntentId: "pi_persist" }),
        }
      )
    ).rejects.toThrow("db down");

    expect(refundBookingPayment).toHaveBeenCalledWith("pi_persist");
  });
});
