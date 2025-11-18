/**
 * @fileoverview Client-side helpers for recording errors on the active span.
 *
 * This module is safe to import from client components and libraries. It
 * encapsulates direct OpenTelemetry API usage so that other modules do not
 * depend on `@opentelemetry/api` directly.
 */

"use client";

import { SpanStatusCode, trace } from "@opentelemetry/api";

/**
 * Records an exception and error status on the active span, if one exists.
 *
 * Intended for client-side error reporting to link errors with the current
 * trace without requiring direct OpenTelemetry imports in callers.
 *
 * @param error - Error instance to record on the active span.
 */
export function recordClientErrorOnActiveSpan(error: Error): void {
  const span = trace.getActiveSpan();
  if (!span) return;

  span.recordException(error);
  span.setStatus({
    code: SpanStatusCode.ERROR,
    message: error.message,
  });
}
