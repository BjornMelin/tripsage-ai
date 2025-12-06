/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Hoisted mocks per testing.md Pattern A
const mockGetServerEnvVar = vi.hoisted(() => vi.fn());
const mockPaymentIntentsCreate = vi.hoisted(() => vi.fn());
const mockPaymentIntentsRetrieve = vi.hoisted(() => vi.fn());
const mockRefundsCreate = vi.hoisted(() => vi.fn());

vi.mock("server-only", () => ({}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: mockGetServerEnvVar,
}));

vi.mock("@/lib/url/server-origin", () => ({
  getRequiredServerOrigin: () => "https://app.tripsage.io",
}));

vi.mock("stripe", () => {
  // Create a class-like constructor for Stripe
  class MockStripe {
    paymentIntents = {
      create: mockPaymentIntentsCreate,
      retrieve: mockPaymentIntentsRetrieve,
    };
    refunds = {
      create: mockRefundsCreate,
    };
  }
  return { default: MockStripe };
});

describe("stripe-client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetServerEnvVar.mockReset();
    mockPaymentIntentsCreate.mockReset();
    mockPaymentIntentsRetrieve.mockReset();
    mockRefundsCreate.mockReset();
  });

  describe("getStripeClient", () => {
    it("throws error when STRIPE_SECRET_KEY is not configured", async () => {
      mockGetServerEnvVar.mockReturnValue(undefined);

      const { getStripeClient } = await import("../stripe-client");

      expect(() => getStripeClient()).toThrow(
        "STRIPE_SECRET_KEY environment variable is required"
      );
    });

    it("creates Stripe client with secret key", async () => {
      mockGetServerEnvVar.mockReturnValue("sk_test_12345");

      const { getStripeClient } = await import("../stripe-client");
      const client = getStripeClient();

      expect(client).toBeDefined();
      expect(client.paymentIntents).toBeDefined();
    });
  });

  describe("createPaymentIntent", () => {
    beforeEach(() => {
      mockGetServerEnvVar.mockReturnValue("sk_test_12345");
    });

    it("creates payment intent with required parameters", async () => {
      const mockIntent = {
        amount: 10000,
        currency: "usd",
        id: "pi_test_123",
        status: "requires_confirmation",
      };
      mockPaymentIntentsCreate.mockResolvedValue(mockIntent);

      const { createPaymentIntent } = await import("../stripe-client");
      const result = await createPaymentIntent({
        amount: 10000,
        currency: "USD",
        paymentMethodId: "pm_test_456",
      });

      expect(result).toEqual(mockIntent);
      expect(mockPaymentIntentsCreate).toHaveBeenCalledWith({
        amount: 10000,
        confirm: true,
        confirmation_method: "manual",
        currency: "usd",
        metadata: {
          source: "accommodation_booking",
        },
        payment_method: "pm_test_456",
        return_url: "https://app.tripsage.io/booking/confirm",
      });
    });

    it("includes customerId when provided", async () => {
      const mockIntent = {
        amount: 10000,
        currency: "usd",
        customer: "cus_test_789",
        id: "pi_test_124",
        status: "succeeded",
      };
      mockPaymentIntentsCreate.mockResolvedValue(mockIntent);

      const { createPaymentIntent } = await import("../stripe-client");
      const result = await createPaymentIntent({
        amount: 10000,
        currency: "USD",
        customerId: "cus_test_789",
        paymentMethodId: "pm_test_456",
      });

      expect(result).toEqual(mockIntent);
      expect(mockPaymentIntentsCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          customer: "cus_test_789",
        })
      );
    });

    it("includes custom metadata when provided", async () => {
      const mockIntent = {
        amount: 5000,
        currency: "eur",
        id: "pi_test_125",
        metadata: {
          booking_id: "b_123",
          source: "accommodation_booking",
        },
        status: "succeeded",
      };
      mockPaymentIntentsCreate.mockResolvedValue(mockIntent);

      const { createPaymentIntent } = await import("../stripe-client");
      await createPaymentIntent({
        amount: 5000,
        currency: "EUR",
        metadata: { booking_id: "b_123" },
        paymentMethodId: "pm_test_456",
      });

      expect(mockPaymentIntentsCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          metadata: {
            booking_id: "b_123",
            source: "accommodation_booking",
          },
        })
      );
    });

    it("propagates Stripe API errors", async () => {
      const stripeError = new Error("Card declined");
      mockPaymentIntentsCreate.mockRejectedValue(stripeError);

      const { createPaymentIntent } = await import("../stripe-client");

      await expect(
        createPaymentIntent({
          amount: 10000,
          currency: "USD",
          paymentMethodId: "pm_test_456",
        })
      ).rejects.toThrow("Card declined");
    });
  });

  describe("refundPayment", () => {
    beforeEach(() => {
      mockGetServerEnvVar.mockReturnValue("sk_test_12345");
    });

    it("creates full refund when amount is not specified", async () => {
      const mockRefund = {
        amount: 10000,
        id: "re_test_123",
        status: "succeeded",
      };
      mockRefundsCreate.mockResolvedValue(mockRefund);

      const { refundPayment } = await import("../stripe-client");
      const result = await refundPayment("pi_test_123");

      expect(result).toEqual(mockRefund);
      expect(mockRefundsCreate).toHaveBeenCalledWith({
        payment_intent: "pi_test_123",
      });
    });

    it("creates partial refund when amount is specified", async () => {
      const mockRefund = {
        amount: 5000,
        id: "re_test_124",
        status: "succeeded",
      };
      mockRefundsCreate.mockResolvedValue(mockRefund);

      const { refundPayment } = await import("../stripe-client");
      const result = await refundPayment("pi_test_123", 5000);

      expect(result).toEqual(mockRefund);
      expect(mockRefundsCreate).toHaveBeenCalledWith({
        amount: 5000,
        payment_intent: "pi_test_123",
      });
    });

    it("propagates refund errors", async () => {
      const refundError = new Error("Charge already refunded");
      mockRefundsCreate.mockRejectedValue(refundError);

      const { refundPayment } = await import("../stripe-client");

      await expect(refundPayment("pi_test_123")).rejects.toThrow(
        "Charge already refunded"
      );
    });
  });

  describe("getPaymentIntent", () => {
    beforeEach(() => {
      mockGetServerEnvVar.mockReturnValue("sk_test_12345");
    });

    it("retrieves payment intent by ID", async () => {
      const mockIntent = {
        amount: 10000,
        currency: "usd",
        id: "pi_test_123",
        status: "succeeded",
      };
      mockPaymentIntentsRetrieve.mockResolvedValue(mockIntent);

      const { getPaymentIntent } = await import("../stripe-client");
      const result = await getPaymentIntent("pi_test_123");

      expect(result).toEqual(mockIntent);
      expect(mockPaymentIntentsRetrieve).toHaveBeenCalledWith("pi_test_123");
    });

    it("propagates retrieval errors", async () => {
      const retrievalError = new Error("Payment intent not found");
      mockPaymentIntentsRetrieve.mockRejectedValue(retrievalError);

      const { getPaymentIntent } = await import("../stripe-client");

      await expect(getPaymentIntent("pi_invalid")).rejects.toThrow(
        "Payment intent not found"
      );
    });
  });
});
