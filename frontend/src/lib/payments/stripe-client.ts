/**
 * @fileoverview Stripe client for payment processing.
 *
 * Server-only module for creating payment intents and processing refunds.
 * Used for accommodation booking payments.
 */

import "server-only";

import Stripe from "stripe";
import { getServerEnvVar } from "@/lib/env/server";
import { getRequiredServerOrigin } from "@/lib/url/server-origin";

/**
 * Get or create Stripe client instance.
 *
 * @returns Stripe client instance
 * @throws {Error} If STRIPE_SECRET_KEY is not configured
 */
export function getStripeClient(): Stripe {
  const secretKey = getServerEnvVar("STRIPE_SECRET_KEY");
  if (!secretKey) {
    throw new Error("STRIPE_SECRET_KEY environment variable is required");
  }
  // Use default API version (latest) - explicitly setting causes type mismatch
  return new Stripe(secretKey, {
    typescript: true,
  });
}

/**
 * Create a payment intent for a booking.
 *
 * @param params - Payment intent parameters
 * @returns Stripe PaymentIntent
 * @throws {Stripe.errors.StripeError} On Stripe API errors
 */
export function createPaymentIntent(params: {
  amount: number; // Amount in cents
  currency: string;
  paymentMethodId: string;
  customerId?: string;
  metadata?: Record<string, string>;
}): Promise<Stripe.PaymentIntent> {
  const stripe = getStripeClient();

  const paymentIntentParams: Stripe.PaymentIntentCreateParams = {
    amount: params.amount,
    confirm: true,
    // biome-ignore lint/style/useNamingConvention: Stripe API uses snake_case
    confirmation_method: "manual",
    currency: params.currency.toLowerCase(),
    metadata: {
      ...params.metadata,
      source: "accommodation_booking",
    },
    // biome-ignore lint/style/useNamingConvention: Stripe API uses snake_case
    payment_method: params.paymentMethodId,
    // biome-ignore lint/style/useNamingConvention: Stripe API uses snake_case
    return_url: `${getRequiredServerOrigin()}/booking/confirm`,
  };

  if (params.customerId) {
    paymentIntentParams.customer = params.customerId;
  }

  return stripe.paymentIntents.create(paymentIntentParams);
}

/**
 * Refund a payment intent.
 *
 * @param paymentIntentId - Stripe payment intent ID
 * @param amount - Optional partial refund amount in cents (full refund if omitted)
 * @returns Stripe Refund
 * @throws {Stripe.errors.StripeError} On Stripe API errors
 */
export function refundPayment(
  paymentIntentId: string,
  amount?: number
): Promise<Stripe.Refund> {
  const stripe = getStripeClient();

  const refundParams: Stripe.RefundCreateParams = {
    // biome-ignore lint/style/useNamingConvention: Stripe API uses snake_case
    payment_intent: paymentIntentId,
  };

  if (amount !== undefined) {
    refundParams.amount = amount;
  }

  return stripe.refunds.create(refundParams);
}

/**
 * Retrieve a payment intent by ID.
 *
 * @param paymentIntentId - Stripe payment intent ID
 * @returns Stripe PaymentIntent
 * @throws {Stripe.errors.StripeError} On Stripe API errors
 */
export function getPaymentIntent(
  paymentIntentId: string
): Promise<Stripe.PaymentIntent> {
  const stripe = getStripeClient();
  return stripe.paymentIntents.retrieve(paymentIntentId);
}
