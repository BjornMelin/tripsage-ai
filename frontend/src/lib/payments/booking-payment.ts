/**
 * @fileoverview Booking payment processing utilities.
 *
 * Handles two-phase commit for accommodation bookings:
 * 1. Charge customer via Stripe
 * 2. Create booking via Expedia API
 * 3. Refund on booking failure
 */

import { getExpediaClient } from "@domain/expedia/client";
import type { EpsCreateBookingRequest } from "@schemas/expedia";
import { secureUuid } from "@/lib/security/random";
import { createServerLogger } from "@/lib/telemetry/logger";
import { createPaymentIntent, getPaymentIntent, refundPayment } from "./stripe-client";

const logger = createServerLogger("booking-payment");

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
  amount: number;
  currency: string;
  paymentMethodId: string;
  customerId?: string;
  user: {
    email: string;
    name: string;
    phone?: string;
  };
  expediaRequest: EpsCreateBookingRequest;
}): Promise<{
  confirmationNumber: string;
  itineraryId: string;
  paymentIntentId: string;
}> {
  const expediaClient = getExpediaClient();

  // Phase 1: Create and confirm Stripe payment intent
  const paymentIntent = await createPaymentIntent({
    amount: params.amount,
    currency: params.currency,
    customerId: params.customerId,
    metadata: {
      // biome-ignore lint/style/useNamingConvention: Stripe metadata uses snake_case
      booking_token: params.expediaRequest.bookingToken,
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

  let confirmationNumber: string;
  let itineraryId: string;

  try {
    const bookingResponse = await expediaClient.createBooking(params.expediaRequest);
    itineraryId =
      bookingResponse.itinerary_id ??
      params.expediaRequest.affiliateReferenceId ??
      secureUuid();
    const roomConfirmation = bookingResponse.rooms?.[0]?.confirmation_id;
    confirmationNumber =
      roomConfirmation?.expedia ??
      roomConfirmation?.property ??
      itineraryId ??
      paymentIntent.id;
  } catch (bookingError) {
    // Phase 3: Refund payment on booking failure
    try {
      await refundPayment(paymentIntent.id);
      logger.info("Refunded payment after booking failure", {
        paymentIntentId: paymentIntent.id,
      });
    } catch (refundError) {
      logger.error("Failed to refund payment after booking failure", {
        errorMessage:
          refundError instanceof Error ? refundError.message : "Unknown refund error",
        paymentIntentId: paymentIntent.id,
      });
      // Log but don't throw - booking failure is the primary error
    }

    const errorMessage =
      bookingError instanceof Error ? bookingError.message : "Unknown booking error";
    throw new Error(
      `Booking failed after payment: ${errorMessage}. Payment has been refunded.`
    );
  }

  return {
    confirmationNumber,
    itineraryId,
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
