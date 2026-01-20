/**
 * @fileoverview Stripe webhook handler with signature verification, idempotency, rate limiting, and telemetry.
 */

import "server-only";

import type { NextRequest, NextResponse } from "next/server";
import type Stripe from "stripe";
import { getServerEnvVar } from "@/lib/env/server";
import {
  PayloadTooLargeError,
  RequestBodyAlreadyReadError,
  readRequestBodyBytesWithLimit,
} from "@/lib/http/body";
import {
  IdempotencyServiceUnavailableError,
  releaseKey,
  tryReserveKey,
} from "@/lib/idempotency/redis";
import { type Span, withTelemetrySpan } from "@/lib/telemetry/span";
import {
  checkWebhookRateLimit,
  createWebhookResponse,
} from "@/lib/webhooks/rate-limit";
import { getStripeClient } from "./stripe-client";

const MAX_WEBHOOK_BYTES = 256 * 1024;
const IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60;

type StripeWebhookResponseBody = Record<string, unknown>;

/**
 * Extracts the Stripe signature header from the request.
 *
 * @param req - The incoming request object.
 * @returns The stripe-signature header value or null if missing.
 */
function getStripeSignatureHeader(req: Request): string | null {
  return req.headers.get("stripe-signature");
}

/**
 * Builds a standardized cache/idempotency key for a Stripe event.
 *
 * @param eventId - The unique Stripe event ID.
 * @returns A formatted event key string.
 */
function buildStripeEventKey(eventId: string): string {
  return `stripe:${eventId}`;
}

/**
 * Records relevant Stripe event attributes to the current telemetry span.
 *
 * @param event - The verified Stripe event.
 * @param span - The active telemetry span.
 */
function recordStripeTelemetry(event: Stripe.Event, span: Span) {
  span.setAttribute("stripe.event_id", event.id);
  span.setAttribute("stripe.event_type", event.type);
  span.setAttribute("stripe.api_version", event.api_version ?? "unknown");
  span.setAttribute("stripe.livemode", event.livemode);
}

/**
 * Processes a verified Stripe event.
 *
 * This function currently serves as a telemetry hook and success acknowledgement.
 * Business logic should branch on event.type here or in downstream handlers.
 *
 * @param event - The verified Stripe event.
 * @param span - The active telemetry span.
 * @returns A promise that resolves when processing is complete.
 */
function handleStripeEvent(event: Stripe.Event, span: Span): Promise<void> {
  // Current implementation is intentionally minimal: record telemetry and acknowledge.
  // Downstream business logic can safely branch on `event.type` without breaking the webhook contract.
  span.addEvent("stripe.event_received", {
    "stripe.event_id": event.id,
    "stripe.event_type": event.type,
  });
  return Promise.resolve();
}

/**
 * Creates a standard success response for the webhook.
 *
 * @param rateLimitResult - The result from the rate limit check.
 * @param body - The JSON body to include in the response.
 * @returns A formatted NextResponse.
 */
function okResponse(
  rateLimitResult: { success: boolean },
  body: StripeWebhookResponseBody
) {
  return createWebhookResponse(rateLimitResult, { body });
}

/**
 * Creates a standard error response for the webhook.
 *
 * @param rateLimitResult - The result from the rate limit check.
 * @param status - The HTTP status code.
 * @param body - The JSON error body.
 * @returns A formatted NextResponse.
 */
function errorResponse(
  rateLimitResult: { success: boolean },
  status: number,
  body: StripeWebhookResponseBody
) {
  return createWebhookResponse(rateLimitResult, { body, status });
}

/**
 * Factory function that creates a POST handler for Stripe webhooks.
 *
 * The handler implements:
 * 1. Rate limiting (fail-closed for reliability).
 * 2. Body size limits and raw byte reading.
 * 3. Stripe signature verification.
 * 4. Redis-backed idempotency to prevent duplicate processing.
 * 5. Comprehensive telemetry and error reporting.
 *
 * @returns An async Next.js route handler function.
 */
export function createStripeWebhookHandler() {
  return async function post(req: NextRequest): Promise<NextResponse> {
    return await withTelemetrySpan(
      "webhook.stripe",
      { attributes: { route: "/api/hooks/stripe" } },
      async (span) => {
        // 1) Rate limit (fail-closed; Stripe will retry)
        // Note: 503 on limiter unavailability triggers Stripe retries.
        // Monitor "webhook.rate_limit_unavailable" attribute for Redis outages.
        const rateLimitResult = await checkWebhookRateLimit(req);

        if (!rateLimitResult.success) {
          if (rateLimitResult.reason === "limiter_unavailable") {
            span.setAttribute("webhook.rate_limit_unavailable", true);
            return errorResponse(rateLimitResult, 503, {
              code: "SERVICE_UNAVAILABLE",
              error: "internal_error",
            });
          }
          span.setAttribute("webhook.rate_limited", true);
          return errorResponse(rateLimitResult, 429, {
            code: "RATE_LIMITED",
            error: "rate_limit_exceeded",
          });
        }

        // 2) Read raw body with hard cap
        let bodyBytes: Uint8Array;
        try {
          bodyBytes = await readRequestBodyBytesWithLimit(req, MAX_WEBHOOK_BYTES);
        } catch (error) {
          if (error instanceof PayloadTooLargeError) {
            span.setAttribute("webhook.payload_too_large", true);
            return errorResponse(rateLimitResult, 413, {
              code: "VALIDATION_ERROR",
              error: "payload_too_large",
            });
          }
          if (error instanceof RequestBodyAlreadyReadError) {
            span.setAttribute("webhook.validation_error", true);
            return errorResponse(rateLimitResult, 400, {
              code: "VALIDATION_ERROR",
              error: "invalid_request",
            });
          }
          span.recordException(
            error instanceof Error ? error : new Error("body_read_error")
          );
          return errorResponse(rateLimitResult, 503, {
            code: "SERVICE_UNAVAILABLE",
            error: "internal_error",
          });
        }

        // 3) Verify Stripe signature
        const signature = getStripeSignatureHeader(req);
        if (!signature) {
          span.setAttribute("webhook.unauthorized", true);
          return errorResponse(rateLimitResult, 401, {
            code: "UNAUTHORIZED",
            error: "missing_signature",
          });
        }

        let event: Stripe.Event;
        try {
          const webhookSecret = getServerEnvVar("STRIPE_WEBHOOK_SECRET");
          const stripe = getStripeClient();
          event = stripe.webhooks.constructEvent(
            Buffer.from(bodyBytes),
            signature,
            webhookSecret
          );
        } catch (error) {
          span.setAttribute("webhook.unauthorized", true);
          span.recordException(
            error instanceof Error ? error : new Error("invalid_signature")
          );
          return errorResponse(rateLimitResult, 401, {
            code: "UNAUTHORIZED",
            error: "invalid_signature",
          });
        }

        recordStripeTelemetry(event, span);

        // 4) Idempotency (Stripe retries aggressively on non-2xx)
        const eventKey = buildStripeEventKey(event.id);
        span.setAttribute("webhook.event_key", eventKey);

        let reserved = false;
        try {
          reserved = await tryReserveKey(eventKey, {
            degradedMode: "fail_closed",
            ttlSeconds: IDEMPOTENCY_TTL_SECONDS,
          });
          if (!reserved) {
            span.setAttribute("webhook.duplicate", true);
            return okResponse(rateLimitResult, { duplicate: true, ok: true });
          }

          // 5) Handle event
          await handleStripeEvent(event, span);

          // Stripe V2.* event notification support: treat unknown types safely.
          if (event.type.startsWith("v2.")) {
            span.setAttribute("stripe.v2_event", true);
          }

          return okResponse(rateLimitResult, {
            eventId: event.id,
            ok: true,
            received: true,
            type: event.type,
          });
        } catch (error) {
          span.recordException(
            error instanceof Error ? error : new Error("webhook_error")
          );

          if (reserved) {
            await releaseKey(eventKey, { degradedMode: "fail_open" }).catch(() => {
              // best-effort rollback only
            });
          }

          if (error instanceof IdempotencyServiceUnavailableError) {
            span.setAttribute("webhook.idempotency_unavailable", true);
            return errorResponse(rateLimitResult, 503, {
              code: "SERVICE_UNAVAILABLE",
              error: "internal_error",
            });
          }

          return errorResponse(rateLimitResult, 500, {
            code: "SERVER_ERROR",
            error: "internal_error",
          });
        }
      }
    );
  };
}
