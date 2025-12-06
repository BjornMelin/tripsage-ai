/** @vitest-environment node */

import type Stripe from "stripe";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock stripe-client before imports
vi.mock("../stripe-client", () => ({
  createPaymentIntent: vi.fn(),
  getPaymentIntent: vi.fn(),
  refundPayment: vi.fn(),
}));

import {
  type ProcessBookingParams,
  processBookingPayment,
  refundBookingPayment,
  verifyPaymentStatus,
} from "../booking-payment";
import { createPaymentIntent, getPaymentIntent, refundPayment } from "../stripe-client";

const mockCreatePaymentIntent = vi.mocked(createPaymentIntent);
const mockGetPaymentIntent = vi.mocked(getPaymentIntent);
const mockRefundPayment = vi.mocked(refundPayment);

describe("booking-payment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("processBookingPayment", () => {
    const validParams: ProcessBookingParams = {
      amount: 10000, // $100.00 in cents
      currency: "USD",
      paymentMethodId: "pm_test_123",
      user: {
        email: "test@example.com",
        name: "Test User",
      },
    };

    it("should successfully process a booking payment", async () => {
      const mockPaymentIntent = {
        amount: 10000,
        currency: "usd",
        id: "pi_test_123",
        status: "succeeded",
      } as Stripe.PaymentIntent;

      mockCreatePaymentIntent.mockResolvedValue(mockPaymentIntent);

      const result = await processBookingPayment(validParams);

      expect(result).toEqual({ paymentIntentId: "pi_test_123" });
      expect(mockCreatePaymentIntent).toHaveBeenCalledWith({
        amount: 10000,
        currency: "USD",
        customerId: undefined,
        metadata: {
          user_email: "test@example.com",
        },
        paymentMethodId: "pm_test_123",
      });
    });

    it("should pass customerId when provided", async () => {
      const paramsWithCustomer: ProcessBookingParams = {
        ...validParams,
        customerId: "cus_test_456",
      };

      const mockPaymentIntent = {
        amount: 10000,
        currency: "usd",
        id: "pi_test_124",
        status: "succeeded",
      } as Stripe.PaymentIntent;

      mockCreatePaymentIntent.mockResolvedValue(mockPaymentIntent);

      const result = await processBookingPayment(paramsWithCustomer);

      expect(result).toEqual({ paymentIntentId: "pi_test_124" });
      expect(mockCreatePaymentIntent).toHaveBeenCalledWith(
        expect.objectContaining({
          customerId: "cus_test_456",
        })
      );
    });

    it("should throw error when payment fails with requires_action status", async () => {
      const mockPaymentIntent = {
        amount: 10000,
        currency: "usd",
        id: "pi_test_125",
        last_payment_error: null,
        status: "requires_action",
      } as Stripe.PaymentIntent;

      mockCreatePaymentIntent.mockResolvedValue(mockPaymentIntent);

      await expect(processBookingPayment(validParams)).rejects.toThrow(
        "Payment failed: requires_action"
      );
    });

    it("should throw error with payment error message when available", async () => {
      const mockPaymentIntent = {
        amount: 10000,
        currency: "usd",
        id: "pi_test_126",
        last_payment_error: {
          code: "card_declined",
          message: "Your card was declined",
          type: "card_error",
        } as Stripe.PaymentIntent.LastPaymentError,
        status: "requires_payment_method",
      } as Stripe.PaymentIntent;

      mockCreatePaymentIntent.mockResolvedValue(mockPaymentIntent);

      await expect(processBookingPayment(validParams)).rejects.toThrow(
        "Payment failed: requires_payment_method. Last payment error: Your card was declined"
      );
    });

    it("should throw error with 'Unknown' when no payment error message", async () => {
      const mockPaymentIntent = {
        amount: 10000,
        currency: "usd",
        id: "pi_test_127",
        last_payment_error: null,
        status: "canceled",
      } as Stripe.PaymentIntent;

      mockCreatePaymentIntent.mockResolvedValue(mockPaymentIntent);

      await expect(processBookingPayment(validParams)).rejects.toThrow(
        "Payment failed: canceled. Last payment error: Unknown"
      );
    });

    it("should propagate Stripe API errors", async () => {
      const stripeError = new Error("Stripe API error");
      mockCreatePaymentIntent.mockRejectedValue(stripeError);

      await expect(processBookingPayment(validParams)).rejects.toThrow(
        "Stripe API error"
      );
    });
  });

  describe("refundBookingPayment", () => {
    it("should process full refund successfully", async () => {
      const mockRefund = {
        amount: 10000,
        id: "re_test_123",
        status: "succeeded",
      } as Stripe.Refund;

      mockRefundPayment.mockResolvedValue(mockRefund);

      const result = await refundBookingPayment("pi_test_123");

      expect(result).toEqual({
        amount: 10000,
        refundId: "re_test_123",
      });
      expect(mockRefundPayment).toHaveBeenCalledWith("pi_test_123", undefined);
    });

    it("should process partial refund successfully", async () => {
      const mockRefund = {
        amount: 5000,
        id: "re_test_124",
        status: "succeeded",
      } as Stripe.Refund;

      mockRefundPayment.mockResolvedValue(mockRefund);

      const result = await refundBookingPayment("pi_test_123", 5000);

      expect(result).toEqual({
        amount: 5000,
        refundId: "re_test_124",
      });
      expect(mockRefundPayment).toHaveBeenCalledWith("pi_test_123", 5000);
    });

    it("should propagate refund errors", async () => {
      const refundError = new Error("Refund failed: charge already refunded");
      mockRefundPayment.mockRejectedValue(refundError);

      await expect(refundBookingPayment("pi_test_123")).rejects.toThrow(
        "Refund failed: charge already refunded"
      );
    });
  });

  describe("verifyPaymentStatus", () => {
    it("should return true for succeeded payment", async () => {
      const mockPaymentIntent = {
        id: "pi_test_123",
        status: "succeeded",
      } as Stripe.PaymentIntent;

      mockGetPaymentIntent.mockResolvedValue(mockPaymentIntent);

      const result = await verifyPaymentStatus("pi_test_123");

      expect(result).toBe(true);
      expect(mockGetPaymentIntent).toHaveBeenCalledWith("pi_test_123");
    });

    it("should return false for requires_action status", async () => {
      const mockPaymentIntent = {
        id: "pi_test_124",
        status: "requires_action",
      } as Stripe.PaymentIntent;

      mockGetPaymentIntent.mockResolvedValue(mockPaymentIntent);

      const result = await verifyPaymentStatus("pi_test_124");

      expect(result).toBe(false);
    });

    it("should return false for processing status", async () => {
      const mockPaymentIntent = {
        id: "pi_test_125",
        status: "processing",
      } as Stripe.PaymentIntent;

      mockGetPaymentIntent.mockResolvedValue(mockPaymentIntent);

      const result = await verifyPaymentStatus("pi_test_125");

      expect(result).toBe(false);
    });

    it("should return false for canceled status", async () => {
      const mockPaymentIntent = {
        id: "pi_test_126",
        status: "canceled",
      } as Stripe.PaymentIntent;

      mockGetPaymentIntent.mockResolvedValue(mockPaymentIntent);

      const result = await verifyPaymentStatus("pi_test_126");

      expect(result).toBe(false);
    });

    it("should propagate retrieval errors", async () => {
      const retrievalError = new Error("Payment intent not found");
      mockGetPaymentIntent.mockRejectedValue(retrievalError);

      await expect(verifyPaymentStatus("pi_invalid")).rejects.toThrow(
        "Payment intent not found"
      );
    });
  });
});
