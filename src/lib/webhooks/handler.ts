/**
 * @fileoverview Webhook handler factory with rate limiting, signature verification, idempotency, and telemetry.
 */

import "server-only";

import type { NextRequest, NextResponse } from "next/server";
import { ZodError } from "zod";
import {
  IdempotencyServiceUnavailableError,
  tryReserveKey,
} from "@/lib/idempotency/redis";
import { type Span, withTelemetrySpan } from "@/lib/telemetry/span";
import {
  WebhookDuplicateError,
  WebhookError,
  type WebhookErrorCode,
  WebhookServiceUnavailableError,
  WebhookValidationError,
} from "./errors";
import { buildEventKey, parseAndVerify, type WebhookPayload } from "./payload";
import { checkWebhookRateLimit, createWebhookResponse } from "./rate-limit";

function normalizeWebhookError(error: unknown): WebhookError {
  if (error instanceof WebhookError) return error;
  if (error instanceof ZodError)
    return new WebhookValidationError("invalid_request", { cause: error });
  if (error instanceof IdempotencyServiceUnavailableError) {
    return new WebhookServiceUnavailableError("service_unavailable", { cause: error });
  }

  const cause = error instanceof Error ? error : new Error("unknown_error");
  return new WebhookError("internal_error", { cause, code: "UNKNOWN", status: 500 });
}

function getSafeErrorMessage(code: WebhookErrorCode, status: number): string {
  const safeMessageMap = new Map<WebhookErrorCode, string>([
    ["VALIDATION_ERROR", "invalid_request"],
    ["UNAUTHORIZED", "unauthorized"],
    ["NOT_FOUND", "not_found"],
    ["CONFLICT", "conflict"],
    ["RATE_LIMITED", "rate_limit_exceeded"],
  ]);

  // 5xx errors always return a generic message to avoid leaking details.
  if (status >= 500) return "internal_error";
  return safeMessageMap.get(code) ?? "invalid_request";
}

// ===== TYPES =====

/**
 * Result returned by a webhook handler.
 */
export type WebhookHandlerResult = Record<string, unknown>;

/**
 * Configuration for creating a webhook handler.
 */
export interface WebhookHandlerConfig<T extends WebhookHandlerResult> {
  /**
   * Name of the webhook handler (used in telemetry span names).
   * Example: "trips", "files", "cache"
   */
  name: string;

  /**
   * Optional table filter - only process webhooks for this table.
   * If not set, all tables are processed.
   */
  tableFilter?: string;

  /**
   * Enable idempotency checking via Redis.
   * When enabled, duplicate events (by event key) are rejected.
   * @default true
   */
  enableIdempotency?: boolean;

  /**
   * TTL for idempotency keys in seconds.
   * @default 300 (5 minutes)
   */
  // biome-ignore lint/style/useNamingConvention: TTL is established acronym for Time To Live
  idempotencyTTL?: number;

  /**
   * Maximum request body size in bytes.
   * @default 65536 (64KB)
   */
  maxBodySize?: number;

  /**
   * Custom handler function to process the webhook payload.
   * Called after all validation and deduplication checks pass.
   *
   * @param payload - Verified webhook payload
   * @param eventKey - Unique event key for this webhook
   * @param span - OpenTelemetry span for adding attributes
   * @param req - Original request (for accessing headers, origin, etc.)
   * @returns Handler result object merged into response JSON
   */
  handle: (
    payload: WebhookPayload,
    eventKey: string,
    span: Span,
    req: NextRequest
  ) => Promise<T>;
}

// ===== HANDLER FACTORY =====

/**
 * Creates a standardized webhook POST handler with built-in:
 * - Rate limiting (returns 429 if exceeded)
 * - Body size validation (returns 413 if too large)
 * - HMAC signature verification (returns 401 if invalid)
 * - Optional table filtering (returns skipped: true for non-matching tables)
 * - Optional idempotency checking (returns duplicate: true for repeated events)
 * - OpenTelemetry span instrumentation
 *
 * @param config - Handler configuration
 * @returns Next.js POST route handler function
 *
 * @example
 * ```ts
 * // src/app/api/hooks/trips/route.ts
 * export const POST = createWebhookHandler({
 *   name: "trips",
 *   tableFilter: "trip_collaborators",
 *   async handle(payload, eventKey, span, req) {
 *     // Custom processing logic
 *     const result = await enqueueJob("notify", { eventKey, payload }, "/api/jobs/notify");
 *     return { enqueued: !!result };
 *   },
 * });
 * ```
 */
export function createWebhookHandler<T extends WebhookHandlerResult>(
  config: WebhookHandlerConfig<T>
) {
  const {
    name,
    tableFilter,
    enableIdempotency = true,
    idempotencyTTL = 300,
    maxBodySize = 65536,
    handle,
  } = config;

  return async function post(req: NextRequest): Promise<NextResponse> {
    return await withTelemetrySpan(
      `webhook.${name}`,
      { attributes: { route: `/api/hooks/${name}` } },
      async (span) => {
        // 1. Rate limiting
        const rateLimitResult = await checkWebhookRateLimit(req);

        // Helper to create responses with rate limit headers attached
        const withRateLimitHeaders = (body: Record<string, unknown>, status?: number) =>
          createWebhookResponse(rateLimitResult, { body, status });

        if (!rateLimitResult.success) {
          if (rateLimitResult.reason === "limiter_unavailable") {
            span.setAttribute("webhook.rate_limit_unavailable", true);
            return withRateLimitHeaders(
              { code: "SERVICE_UNAVAILABLE", error: "internal_error" },
              503
            );
          }

          span.setAttribute("webhook.rate_limited", true);
          return withRateLimitHeaders(
            { code: "RATE_LIMITED", error: "rate_limit_exceeded" },
            429
          );
        }

        // 2. Body size validation
        const contentLengthHeader = req.headers.get("content-length");
        const parsedContentLength = contentLengthHeader?.trim()
          ? Number.parseInt(contentLengthHeader.trim(), 10)
          : Number.NaN;
        const contentLength =
          Number.isFinite(parsedContentLength) && parsedContentLength > 0
            ? parsedContentLength
            : 0;
        if (contentLength > maxBodySize) {
          span.setAttribute("webhook.payload_too_large", true);
          return withRateLimitHeaders(
            { code: "VALIDATION_ERROR", error: "payload_too_large" },
            413
          );
        }

        // 3. Parse and verify HMAC signature
        const verification = await parseAndVerify(req, { maxBytes: maxBodySize });
        if (!verification.ok) {
          if (verification.reason === "payload_too_large") {
            span.setAttribute("webhook.payload_too_large", true);
            return withRateLimitHeaders(
              { code: "VALIDATION_ERROR", error: "payload_too_large" },
              413
            );
          }
          if (
            verification.reason === "invalid_json" ||
            verification.reason === "invalid_payload_shape"
          ) {
            span.setAttribute("webhook.validation_error", true);
            return withRateLimitHeaders(
              { code: "VALIDATION_ERROR", error: "invalid_request" },
              400
            );
          }
          if (
            verification.reason === "missing_secret_env" ||
            verification.reason === "body_read_error"
          ) {
            span.setAttribute("webhook.error", true);
            span.setAttribute("webhook.error_code", "SERVICE_UNAVAILABLE");
            span.setAttribute("webhook.error_status", 503);
            return withRateLimitHeaders(
              { code: "SERVICE_UNAVAILABLE", error: "internal_error" },
              503
            );
          }
          span.setAttribute("webhook.unauthorized", true);
          return withRateLimitHeaders(
            { code: "UNAUTHORIZED", error: "invalid_signature" },
            401
          );
        }

        const payload = verification.payload;
        if (!payload) {
          span.setAttribute("webhook.unauthorized", true);
          return withRateLimitHeaders(
            { code: "UNAUTHORIZED", error: "invalid_signature" },
            401
          );
        }
        span.setAttribute("webhook.table", payload.table);
        span.setAttribute("webhook.op", payload.type);

        // 4. Build event key (used for global idempotency across handlers)
        const eventKey = buildEventKey(payload);
        span.setAttribute("webhook.event_key", eventKey);

        try {
          // 5. Idempotency check (global)
          if (enableIdempotency) {
            span.setAttribute("webhook.idempotency_scope", "global");
            const unique = await tryReserveKey(eventKey, {
              degradedMode: "fail_closed",
              ttlSeconds: idempotencyTTL,
            });
            if (!unique) {
              span.setAttribute("webhook.duplicate", true);
              return withRateLimitHeaders({ duplicate: true, ok: true });
            }
          }

          // 6. Table filtering (post-idempotency to prevent duplicate processing
          // across multiple handlers that may receive the same event)
          if (tableFilter && payload.table !== tableFilter) {
            span.setAttribute("webhook.skipped", true);
            span.setAttribute("webhook.skip_reason", "table_mismatch");
            return withRateLimitHeaders({ ok: true, skipped: true });
          }

          const result = await handle(payload, eventKey, span, req);
          return withRateLimitHeaders({ ok: true, ...result });
        } catch (error) {
          const exception =
            error instanceof Error
              ? error
              : new Error(typeof error === "string" ? error : "error");
          span.recordException(exception);
          span.setAttribute("webhook.error", true);

          const webhookError = normalizeWebhookError(error);
          span.setAttribute("webhook.error_code", webhookError.code);
          span.setAttribute("webhook.error_status", webhookError.status);
          if (exception.message) {
            span.setAttribute("webhook.error_message", exception.message);
          }

          if (webhookError instanceof WebhookDuplicateError) {
            return withRateLimitHeaders({ duplicate: true, ok: true });
          }

          const response = withRateLimitHeaders(
            {
              code: webhookError.code,
              error: getSafeErrorMessage(webhookError.code, webhookError.status),
            },
            webhookError.status
          );

          if (webhookError.retryAfterSeconds != null) {
            response.headers.set("Retry-After", String(webhookError.retryAfterSeconds));
          }

          return response;
        }
      }
    );
  };
}

// ===== EXPORTS =====

export type { WebhookPayload } from "./payload";
