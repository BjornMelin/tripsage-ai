/**
 * @fileoverview Standardized API error response helpers.
 *
 * Provides unified error response format across all API routes.
 */

import { NextResponse } from "next/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("api-error-response");

/** Standard API error response structure. */
export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: unknown;
  timestamp: string;
}

/**
 * Creates a standardized API error response object.
 *
 * @param code - Error code identifier (e.g., "INVALID_CONTENT_TYPE")
 * @param message - Human-readable error message
 * @param details - Optional additional error details
 * @returns Standardized error response object
 *
 * @example
 * ```typescript
 * return NextResponse.json(
 *   createApiError("INVALID_CONTENT_TYPE", "Invalid content type", { contentType }),
 *   { status: 400 }
 * );
 * ```
 */
export function createApiError(
  code: string,
  message: string,
  details?: unknown
): ApiErrorResponse {
  return {
    code,
    message,
    ...(details ? { details } : {}),
    timestamp: new Date().toISOString(),
  };
}

/**
 * Unified error response format used across all API routes.
 */
export interface UnifiedApiError {
  error: string;
  reason: string;
  details?: unknown;
  timestamp?: string;
}

/**
 * Creates a unified error response NextResponse.
 *
 * This is the preferred method for all API routes as it provides:
 * - Consistent error format
 * - Automatic logging with redaction
 * - Type safety
 *
 * @param options - Error response options
 * @param options.error - Error code identifier (e.g., "invalid_request", "unauthorized")
 * @param options.reason - Human-readable error message
 * @param options.status - HTTP status code
 * @param options.details - Optional additional error details
 * @param options.err - Optional error object to log (will be redacted)
 * @returns NextResponse with standardized error format
 *
 * @example
 * ```typescript
 * return createUnifiedErrorResponse({
 *   error: "invalid_request",
 *   reason: "Missing required field",
 *   status: 400,
 *   details: { field: "email" }
 * });
 * ```
 */
export function createUnifiedErrorResponse({
  error,
  reason,
  status,
  details,
  err,
}: {
  error: string;
  reason: string;
  status: number;
  details?: unknown;
  err?: unknown;
}): NextResponse {
  if (err) {
    const errorMessage =
      err instanceof Error ? err.message : String(err ?? "Unknown error");
    // Redact sensitive patterns
    const redactedMessage = errorMessage
      .replace(/sk-[a-zA-Z0-9]{20,}/g, "[REDACTED]")
      .replace(/api[_-]?key["\s:=]+([a-zA-Z0-9_-]{10,})/gi, 'api_key="[REDACTED]"')
      .replace(/token["\s:=]+([a-zA-Z0-9_-]{10,})/gi, 'token="[REDACTED]"')
      .replace(/secret["\s:=]+([a-zA-Z0-9_-]{10,})/gi, 'secret="[REDACTED]"');

    logger.error("api.error", {
      error,
      message: redactedMessage,
      reason,
      status,
    });
  }

  const body: UnifiedApiError = {
    error,
    reason,
    timestamp: new Date().toISOString(),
  };

  if (details) {
    body.details = details;
  }

  return NextResponse.json(body, { status });
}
