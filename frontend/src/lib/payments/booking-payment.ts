/**
 * @fileoverview Booking payment processing utilities.
 *
 * Handles payment authorization/charge and refunds for accommodation bookings.
 */

import { createPaymentIntent, getPaymentIntent, refundPayment } from "./stripe-client";

/**
 * Process booking payment and create Expedia booking.
 *
 * @param params - Booking payment parameters
 * @returns Payment confirmation details
 * @throws {Error} On payment failures
 */
export type ProcessBookingParams = {
  amount: number;
  currency: string;
  paymentMethodId: string;
  customerId?: string;
  user: {
    email: string;
    name: string;
    phone?: string;
  };
};

export type ProcessedPayment = {
  paymentIntentId: string;
};

export async function processBookingPayment(
  params: ProcessBookingParams
): Promise<ProcessedPayment> {
  const paymentIntent = await createPaymentIntent({
    amount: params.amount,
    currency: params.currency,
    customerId: params.customerId,
    metadata: {
      // biome-ignore lint/style/useNamingConvention: Stripe metadata uses snake_case
      user_email: params.user.email,
    },
    paymentMethodId: params.paymentMethodId,
  });

  if (paymentIntent.status !== "succeeded") {
    throw new Error(
      `Payment failed: ${paymentIntent.status}. ` +
        `Last payment error: ${paymentIntent.last_payment_error?.message || "Unknown"}`
    );
  }

  return {
    paymentIntentId: paymentIntent.id,
  };
}

/**
 * Refund a booking payment.
 *
 * @param paymentIntentId - Stripe payment intent ID
 * @param amount - Optional partial refund amount in cents
 * @returns Refund confirmation
 */
export async function refundBookingPayment(
  paymentIntentId: string,
  amount?: number
): Promise<{ refundId: string; amount: number }> {
  const refund = await refundPayment(paymentIntentId, amount);

  return {
    amount: refund.amount,
    refundId: refund.id,
  };
}

/**
 * Verify payment intent status before proceeding with booking.
 *
 * @param paymentIntentId - Stripe payment intent ID
 * @returns True if payment is confirmed, false otherwise
 */
export async function verifyPaymentStatus(paymentIntentId: string): Promise<boolean> {
  const paymentIntent = await getPaymentIntent(paymentIntentId);
  return paymentIntent.status === "succeeded";
}
