/**
 * @fileoverview Stripe webhook handler for payment events.
 */

import "server-only";

import { createStripeWebhookHandler } from "@/lib/payments/stripe-webhook";

export const POST = createStripeWebhookHandler();
