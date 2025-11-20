import { runBookingOrchestrator } from "@domain/accommodations/booking-orchestrator";
import { ProviderError } from "@domain/accommodations/errors";
import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import type {
  EpsCreateBookingRequest,
  EpsCreateBookingResponse,
} from "@schemas/expedia";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { refundBookingPayment } from "@/lib/payments/booking-payment";
import type { TypedServerSupabase } from "@/lib/supabase/server";

vi.mock("@/lib/payments/booking-payment", () => ({
  refundBookingPayment: vi.fn(async () => undefined),
}));

const providerOk: AccommodationProviderAdapter = {
  checkAvailability: vi.fn(),
  createBooking: vi.fn(
    async (_params: EpsCreateBookingRequest) =>
      ({
        ok: true as const,
        retries: 0,
        value: {
          itinerary_id: "it-1",
          rooms: [{ confirmation_id: { expedia: "cn-1" } }],
        } as EpsCreateBookingResponse,
      }) satisfies ReturnType<
        AccommodationProviderAdapter["createBooking"]
      > extends Promise<infer R>
        ? R
        : never
  ),
  getPropertyDetails: vi.fn(),
  name: "expedia",
  priceCheck: vi.fn(),
  searchAvailability: vi.fn(),
};

const providerFail: AccommodationProviderAdapter = {
  ...providerOk,
  createBooking: vi.fn(
    async (_params: EpsCreateBookingRequest) =>
      ({
        error: new ProviderError("provider_failed", "fail"),
        ok: false as const,
        retries: 1,
      }) satisfies ReturnType<
        AccommodationProviderAdapter["createBooking"]
      > extends Promise<infer R>
        ? R
        : never
  ),
};

const supabaseStub = {} as unknown as TypedServerSupabase;

describe("BookingOrchestrator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("refunds when provider booking fails after payment", async () => {
    await expect(
      runBookingOrchestrator(
        { provider: providerFail, supabase: supabaseStub },
        {
          amount: 100,
          approvalKey: "bookAccommodation",
          bookingToken: "tok",
          currency: "USD",
          guest: { email: "a@b.com", name: "Tester" },
          idempotencyKey: "idemp",
          paymentMethodId: "pm_1",
          persistBooking: vi.fn(),
          processPayment: async () => ({ paymentIntentId: "pi_123" }),
          providerPayload: {
            billingContact: {
              address: { city: "Unknown", countryCode: "US", line1: "None" },
              familyName: "t",
              givenName: "t",
            },
            bookingToken: "tok",
            contact: {
              email: "a@b.com",
              phoneCountryCode: "1",
              phoneNumber: "1234567",
            },
            stay: { adults: 1, checkIn: "2025-01-01", checkOut: "2025-01-02" },
            traveler: { familyName: "t", givenName: "t" },
          },
          requestApproval: async () => undefined,
          sessionId: "s1",
          stay: {
            checkin: "2025-01-01",
            checkout: "2025-01-02",
            guests: 1,
            listingId: "l1",
          },
          userId: "u1",
        }
      )
    ).rejects.toBeTruthy();

    expect(refundBookingPayment).toHaveBeenCalledWith("pi_123");
  });

  test("refunds when provider throws", async () => {
    const throwingProvider: AccommodationProviderAdapter = {
      ...providerOk,
      createBooking: vi.fn(() => {
        throw new Error("network");
      }),
    };

    await expect(
      runBookingOrchestrator(
        { provider: throwingProvider, supabase: supabaseStub },
        {
          amount: 100,
          approvalKey: "bookAccommodation",
          bookingToken: "tok",
          currency: "USD",
          guest: { email: "a@b.com", name: "Tester" },
          idempotencyKey: "idemp",
          paymentMethodId: "pm_1",
          persistBooking: vi.fn(),
          processPayment: async () => ({ paymentIntentId: "pi_123" }),
          providerPayload: {
            billingContact: {
              address: { city: "Unknown", countryCode: "US", line1: "None" },
              familyName: "t",
              givenName: "t",
            },
            bookingToken: "tok",
            contact: {
              email: "a@b.com",
              phoneCountryCode: "1",
              phoneNumber: "1234567",
            },
            stay: { adults: 1, checkIn: "2025-01-01", checkOut: "2025-01-02" },
            traveler: { familyName: "t", givenName: "t" },
          },
          requestApproval: async () => undefined,
          sessionId: "s1",
          stay: {
            checkin: "2025-01-01",
            checkout: "2025-01-02",
            guests: 1,
            listingId: "l1",
          },
          userId: "u1",
        }
      )
    ).rejects.toBeTruthy();

    expect(refundBookingPayment).toHaveBeenCalledWith("pi_123");
  });

  test("propagates persistence failure", async () => {
    const persistSpy = vi.fn(() => {
      throw new Error("db");
    });

    await expect(
      runBookingOrchestrator(
        { provider: providerOk, supabase: supabaseStub },
        {
          amount: 100,
          approvalKey: "bookAccommodation",
          bookingToken: "tok",
          currency: "USD",
          guest: { email: "a@b.com", name: "Tester" },
          idempotencyKey: "idemp",
          paymentMethodId: "pm_1",
          persistBooking: persistSpy,
          processPayment: async () => ({ paymentIntentId: "pi_999" }),
          providerPayload: {
            billingContact: {
              address: { city: "Unknown", countryCode: "US", line1: "None" },
              familyName: "t",
              givenName: "t",
            },
            bookingToken: "tok",
            contact: {
              email: "a@b.com",
              phoneCountryCode: "1",
              phoneNumber: "1234567",
            },
            stay: { adults: 1, checkIn: "2025-01-01", checkOut: "2025-01-02" },
            traveler: { familyName: "t", givenName: "t" },
          },
          requestApproval: async () => undefined,
          sessionId: "s1",
          stay: {
            checkin: "2025-01-01",
            checkout: "2025-01-02",
            guests: 1,
            listingId: "l1",
          },
          userId: "u1",
        }
      )
    ).rejects.toBeTruthy();

    expect(persistSpy).toHaveBeenCalled();
  });

  test("returns booking result when provider succeeds", async () => {
    const result = await runBookingOrchestrator(
      { provider: providerOk, supabase: supabaseStub },
      {
        amount: 100,
        approvalKey: "bookAccommodation",
        bookingToken: "tok",
        currency: "USD",
        guest: { email: "a@b.com", name: "Tester" },
        idempotencyKey: "idemp",
        paymentMethodId: "pm_1",
        persistBooking: vi.fn(),
        processPayment: async () => ({ paymentIntentId: "pi_123" }),
        providerPayload: {
          billingContact: {
            address: { city: "Unknown", countryCode: "US", line1: "None" },
            familyName: "t",
            givenName: "t",
          },
          bookingToken: "tok",
          contact: {
            email: "a@b.com",
            phoneCountryCode: "1",
            phoneNumber: "1234567",
          },
          stay: { adults: 1, checkIn: "2025-01-01", checkOut: "2025-01-02" },
          traveler: { familyName: "t", givenName: "t" },
        },
        requestApproval: async () => undefined,
        sessionId: "s1",
        stay: {
          checkin: "2025-01-01",
          checkout: "2025-01-02",
          guests: 1,
          listingId: "l1",
        },
        userId: "u1",
      }
    );

    expect(result.status).toBe("success");
    expect(result.bookingStatus).toBe("confirmed");
  });
});
