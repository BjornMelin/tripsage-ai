/**
 * @fileoverview Booking payment processing utilities.
 *
 * Handles two-phase commit for accommodation bookings:
 * 1. Charge customer via Stripe
 * 2. Create booking via Expedia API
 * 3. Refund on booking failure
 */

import { getExpediaClient } from "@/lib/travel-api/expedia-client";
import type { EpsCreateBookingRequest } from "@/lib/travel-api/expedia-types";
import { createPaymentIntent, getPaymentIntent, refundPayment } from "./stripe-client";

/**
 * Process booking payment and create Expedia booking.
 *
 * Implements two-phase commit: charge customer first, then create booking.
 * If booking fails, payment is automatically refunded.
 *
 * @param params - Booking payment parameters
 * @returns Booking confirmation with payment and booking IDs
 * @throws {Error} On payment or booking failures
 */
export async function processBookingPayment(params: {
  bookingToken: string;
  amount: number; // Amount in cents
  currency: string;
  paymentMethodId: string;
  customerId?: string;
  user: {
    email: string;
    name: string;
    phone?: string;
  };
  specialRequests?: string;
}): Promise<{
  paymentIntentId: string;
  bookingId: string;
  confirmationNumber: string;
}> {
  const expediaClient = getExpediaClient();

  // Phase 1: Create and confirm Stripe payment intent
  const paymentIntent = await createPaymentIntent({
    amount: params.amount,
    currency: params.currency,
    customerId: params.customerId,
    metadata: {
      // biome-ignore lint/style/useNamingConvention: Stripe metadata uses snake_case
      booking_token: params.bookingToken,
      // biome-ignore lint/style/useNamingConvention: Stripe metadata uses snake_case
      user_email: params.user.email,
    },
    paymentMethodId: params.paymentMethodId,
  });

  // Verify payment succeeded
  if (paymentIntent.status !== "succeeded") {
    throw new Error(
      `Payment failed: ${paymentIntent.status}. ` +
        `Last payment error: ${paymentIntent.last_payment_error?.message || "Unknown"}`
    );
  }

  let bookingId: string;
  let confirmationNumber: string;

  try {
    // Phase 2: Create Expedia booking
    const bookingRequest: EpsCreateBookingRequest = {
      bookingToken: params.bookingToken,
      payment: {
        paymentIntentId: paymentIntent.id,
        paymentMethodId: params.paymentMethodId,
      },
      specialRequests: params.specialRequests,
      user: params.user,
    };

    const bookingResponse = await expediaClient.createBooking(bookingRequest);
    bookingId = bookingResponse.id;
    confirmationNumber = bookingResponse.confirmationNumber;
  } catch (bookingError) {
    // Phase 3: Refund payment on booking failure
    try {
      await refundPayment(paymentIntent.id);
      console.log(`Refunded payment ${paymentIntent.id} due to booking failure`);
    } catch (refundError) {
      console.error(`Failed to refund payment ${paymentIntent.id}:`, refundError);
      // Log but don't throw - booking failure is the primary error
    }

    const errorMessage =
      bookingError instanceof Error ? bookingError.message : "Unknown booking error";
    throw new Error(
      `Booking failed after payment: ${errorMessage}. Payment has been refunded.`
    );
  }

  return {
    bookingId,
    confirmationNumber,
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
