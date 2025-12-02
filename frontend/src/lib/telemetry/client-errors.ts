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
 * Metadata to attach to error spans for debugging context.
 */
export interface ErrorSpanMetadata {
  /** Component or module context */
  context?: string;
  /** Action being performed when error occurred */
  action?: string;
  /** Additional metadata */
  [key: string]: unknown;
}

/**
 * Records an exception and error status on the active span, if one exists.
 *
 * Intended for client-side error reporting to link errors with the current
 * trace without requiring direct OpenTelemetry imports in callers.
 *
 * @param error - Error instance to record on the active span.
 * @param metadata - Optional metadata to attach as span attributes.
 */
export function recordClientErrorOnActiveSpan(
  error: Error,
  metadata?: ErrorSpanMetadata
): void {
  const span = trace.getActiveSpan();
  if (!span) return;

  span.recordException(error);
  span.setStatus({
    code: SpanStatusCode.ERROR,
    message: error.message,
  });

  // Add optional metadata as span attributes
  if (metadata) {
    for (const [key, value] of Object.entries(metadata)) {
      if (value !== undefined && value !== null) {
        // Only set primitive values as attributes
        if (
          typeof value === "string" ||
          typeof value === "number" ||
          typeof value === "boolean"
        ) {
          span.setAttribute(`error.${key}`, value);
        }
      }
    }
  }
}
