/**
 * @fileoverview Client-side helpers for recording errors on the active span.
 */

"use client";

import { SpanStatusCode, trace } from "@opentelemetry/api";
import {
  buildSanitizedErrorForTelemetry,
  sanitizeClientErrorMessage,
} from "./client-sanitize";
import {
  MAX_ERROR_MESSAGE_LENGTH,
  REDACTED_VALUE,
  SENSITIVE_METADATA_KEY_RE,
} from "./constants";

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
 * Sanitizes a metadata value for span attributes by applying redaction and truncation.
 *
 * @param key - Metadata key name to check for sensitive patterns.
 * @param value - Value to sanitize.
 * @returns Sanitized value: redacted if key is sensitive, truncated if string is too long, otherwise unchanged.
 */
function sanitizeMetadataValue(key: string, value: string): string {
  if (SENSITIVE_METADATA_KEY_RE.test(key)) {
    return REDACTED_VALUE;
  }
  if (value.length > MAX_ERROR_MESSAGE_LENGTH) {
    // Truncate and add ellipsis indicator (total length stays within limit)
    return `${value.slice(0, MAX_ERROR_MESSAGE_LENGTH - 3)}...`;
  }
  return value;
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

  const sanitizedMessage = sanitizeClientErrorMessage(error.message);
  const exceptionError =
    sanitizedMessage.redacted || sanitizedMessage.truncated
      ? buildSanitizedErrorForTelemetry(error, sanitizedMessage.message)
      : error;

  span.recordException(exceptionError);
  span.setStatus({ code: SpanStatusCode.ERROR, message: sanitizedMessage.message });
  if (sanitizedMessage.redacted) {
    span.setAttribute("error.message_redacted", true);
  }
  if (sanitizedMessage.truncated) {
    span.setAttribute("error.message_truncated", true);
  }

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
          const attributeKey = `error.${key}`;
          const attributeValue =
            typeof value === "string" ? sanitizeMetadataValue(key, value) : value;
          span.setAttribute(attributeKey, attributeValue);
        }
      }
    }
  }
}
