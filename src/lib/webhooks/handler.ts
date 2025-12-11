/**
 * @fileoverview Webhook handler abstraction to reduce code duplication.
 *
 * Provides a factory function that creates standardized webhook handlers with:
 * - Rate limiting
 * - Body size validation
 * - HMAC signature verification
 * - Table filtering (optional)
 * - Idempotency via Redis (optional)
 * - OpenTelemetry instrumentation
 *
 * Reduces ~75 lines of duplicated boilerplate per handler to ~25 lines.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { ZodError } from "zod";
import { tryReserveKey } from "@/lib/idempotency/redis";
import { type Span, withTelemetrySpan } from "@/lib/telemetry/span";
import { buildEventKey, parseAndVerify, type WebhookPayload } from "./payload";
import { checkWebhookRateLimit, createRateLimitHeaders } from "./rate-limit";

// ===== ERROR CLASSIFICATION =====

/**
 * Known error codes for classification.
 */
type ErrorCode =
  | "VALIDATION_ERROR"
  | "NOT_FOUND"
  | "CONFLICT"
  | "SERVICE_UNAVAILABLE"
  | "TIMEOUT"
  | "UNKNOWN";

/** Type guard to check if error has a code property. */
function hasErrorCode(error: unknown): error is Error & { code: string } {
  return (
    error instanceof Error &&
    "code" in error &&
    typeof (error as { code: unknown }).code === "string"
  );
}

/**
 * Classifies an error and returns the appropriate HTTP status code.
 *
 * Uses concrete error classes and standardized error codes first,
 * falling back to message heuristics for legacy/unknown errors.
 * Prefer throwing typed errors with explicit codes; the heuristics are
 * best-effort and may misclassify localized/custom messages.
 *
 * @param error - The error to classify
 * @returns Object with status code and error code
 */
export function classifyError(error: unknown): { status: number; code: ErrorCode } {
  if (!(error instanceof Error)) {
    return { code: "UNKNOWN", status: 500 };
  }

  // 1. Check concrete error classes first (most reliable)
  if (error instanceof ZodError) {
    return { code: "VALIDATION_ERROR", status: 400 };
  }

  // 2. Check standardized error codes (if present)
  if (hasErrorCode(error)) {
    switch (error.code) {
      case "VALIDATION_ERROR":
      case "INVALID_INPUT":
        return { code: "VALIDATION_ERROR", status: 400 };
      case "NOT_FOUND":
      case "ENOENT":
        return { code: "NOT_FOUND", status: 404 };
      case "CONFLICT":
      case "DUPLICATE":
        return { code: "CONFLICT", status: 409 };
      case "SERVICE_UNAVAILABLE":
      case "CIRCUIT_OPEN":
      case "ECONNREFUSED":
        return { code: "SERVICE_UNAVAILABLE", status: 503 };
      case "TIMEOUT":
      case "ETIMEDOUT":
      case "ESOCKETTIMEDOUT":
        return { code: "TIMEOUT", status: 504 };
    }
  }

  // 3. Fall back to message/name heuristics for legacy errors.
  // Prefer throwing typed errors with explicit codes; keep these heuristics in sync with
  // real error payloads to avoid misclassification (especially for localized messages).
  const message = error.message.toLowerCase();
  const name = error.name.toLowerCase();

  // Validation errors -> 400
  if (
    name.includes("validation") ||
    name.includes("zod") ||
    message.includes("invalid") ||
    message.includes("required") ||
    message.includes("must be")
  ) {
    return { code: "VALIDATION_ERROR", status: 400 };
  }

  // Not found errors -> 404
  if (message.includes("not found") || message.includes("does not exist")) {
    return { code: "NOT_FOUND", status: 404 };
  }

  // Conflict/duplicate errors -> 409
  if (
    message.includes("already exists") ||
    message.includes("duplicate") ||
    message.includes("conflict")
  ) {
    return { code: "CONFLICT", status: 409 };
  }

  // Service unavailable / circuit breaker -> 503
  if (
    message.includes("circuit open") ||
    message.includes("service unavailable") ||
    message.includes("temporarily unavailable") ||
    message.includes("rate limit") ||
    name.includes("serviceerror")
  ) {
    return { code: "SERVICE_UNAVAILABLE", status: 503 };
  }

  // Timeout errors -> 504
  if (
    message.includes("timeout") ||
    message.includes("timed out") ||
    name.includes("timeout")
  ) {
    return { code: "TIMEOUT", status: 504 };
  }

  // Default to 500 for unknown errors
  return { code: "UNKNOWN", status: 500 };
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
        if (!rateLimitResult.success) {
          span.setAttribute("webhook.rate_limited", true);
          return new NextResponse(JSON.stringify({ error: "rate_limit_exceeded" }), {
            headers: {
              "Content-Type": "application/json",
              ...createRateLimitHeaders(rateLimitResult),
            },
            status: 429,
          });
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
          return NextResponse.json({ error: "payload_too_large" }, { status: 413 });
        }

        // 3. Parse and verify HMAC signature
        const { ok, payload } = await parseAndVerify(req);
        if (!ok || !payload) {
          span.setAttribute("webhook.unauthorized", true);
          return NextResponse.json({ error: "invalid_signature" }, { status: 401 });
        }

        span.setAttribute("webhook.table", payload.table);
        span.setAttribute("webhook.op", payload.type);

        // 4. Build event key (used for global idempotency across handlers)
        const eventKey = buildEventKey(payload);
        span.setAttribute("webhook.event_key", eventKey);

        // 5. Idempotency check (global)
        if (enableIdempotency) {
          span.setAttribute("webhook.idempotency_scope", "global");
          const unique = await tryReserveKey(eventKey, idempotencyTTL);
          if (!unique) {
            span.setAttribute("webhook.duplicate", true);
            return NextResponse.json({ duplicate: true, ok: true });
          }
        }

        // 6. Table filtering (post-idempotency to prevent duplicate processing
        // across multiple handlers that may receive the same event)
        if (tableFilter && payload.table !== tableFilter) {
          span.setAttribute("webhook.skipped", true);
          span.setAttribute("webhook.skip_reason", "table_mismatch");
          return NextResponse.json({ ok: true, skipped: true });
        }

        // 7. Execute custom handler with error classification
        try {
          const result = await handle(payload, eventKey, span, req);
          return NextResponse.json({ ok: true, ...result });
        } catch (error) {
          span.recordException(error as Error);
          span.setAttribute("webhook.error", true);

          // M6: Classify error to return appropriate status code
          const { status, code } = classifyError(error);
          span.setAttribute("webhook.error_code", code);
          span.setAttribute("webhook.error_status", status);
          if (error instanceof Error) {
            span.setAttribute("webhook.error_message", error.message);
          }

          const safeMessage =
            status >= 500
              ? "internal_error"
              : code === "VALIDATION_ERROR"
                ? "invalid_request"
                : code === "NOT_FOUND"
                  ? "not_found"
                  : code === "CONFLICT"
                    ? "conflict"
                    : code === "SERVICE_UNAVAILABLE"
                      ? "service_unavailable"
                      : code === "TIMEOUT"
                        ? "timeout"
                        : "internal_error";

          return NextResponse.json({ code, error: safeMessage }, { status });
        }
      }
    );
  };
}

// ===== EXPORTS =====

export type { WebhookPayload } from "./payload";
