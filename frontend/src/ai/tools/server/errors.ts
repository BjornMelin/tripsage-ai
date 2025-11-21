/**
 * @fileoverview Canonical tool error helpers for AI tools.
 *
 * Centralizes error codes and constructors to ensure consistent error handling
 * across all AI tools and agents. Runtime-only; schemas live under
 * `@ai/tools/schemas/tools`.
 */

import "server-only";

import type { ToolError, ToolErrorCode } from "@ai/tools/schemas/tools";
import { toolErrorSchema } from "@ai/tools/schemas/tools";

// Re-export types from schemas so callers only depend on this runtime module.
export type { ToolError, ToolErrorCode };

/**
 * Tool error codes organized by category.
 *
 * Each tool namespace has its own error codes for clarity and observability.
 * Property names use camelCase per TypeScript conventions; string values use
 * snake_case for API/log compatibility.
 */
export const TOOL_ERROR_CODES = {
  accomAvailabilityFailed: "accom_availability_failed",
  accomAvailabilityNotFound: "accom_availability_not_found",
  accomAvailabilityRateLimited: "accom_availability_rate_limited",
  accomAvailabilityUnauthorized: "accom_availability_unauthorized",
  accomBookingFailed: "accom_booking_failed",
  accomBookingSessionRequired: "accom_booking_session_required",
  accomDetailsFailed: "accom_details_failed",
  accomDetailsNotConfigured: "accom_details_not_configured",
  accomDetailsNotFound: "accom_details_not_found",
  accomDetailsRateLimited: "accom_details_rate_limited",
  accomDetailsTimeout: "accom_details_timeout",
  accomDetailsUnauthorized: "accom_details_unauthorized",
  accomSearchFailed: "accom_search_failed",

  // Accommodation errors
  accomSearchNotConfigured: "accom_search_not_configured",
  accomSearchPaymentRequired: "accom_search_payment_required",
  accomSearchRateLimited: "accom_search_rate_limited",
  accomSearchTimeout: "accom_search_timeout",
  accomSearchUnauthorized: "accom_search_unauthorized",

  // Approval errors
  approvalBackendUnavailable: "approval_backend_unavailable",
  approvalMissingSession: "approval_missing_session",
  approvalRequired: "approval_required",

  // General tool errors
  toolExecutionFailed: "tool_execution_failed",
  toolRateLimited: "tool_rate_limited",
  webSearchError: "web_search_error",
  webSearchFailed: "web_search_failed",

  // Web search errors
  webSearchNotConfigured: "web_search_not_configured",
  webSearchPaymentRequired: "web_search_payment_required",
  webSearchRateLimited: "web_search_rate_limited",
  webSearchUnauthorized: "web_search_unauthorized",
} as const;

/**
 * Create a standardized tool error.
 *
 * @param code Error code from TOOL_ERROR_CODES.
 * @param message Optional error message (defaults to code).
 * @param meta Optional metadata for observability.
 * @returns ToolError instance (validated via Zod schema).
 */
export function createToolError(
  code: ToolErrorCode,
  message?: string,
  meta?: Record<string, unknown>
): ToolError {
  const error = new Error(message ?? code) as ToolError;
  // Normalize name to satisfy tooling/schema expectations.
  error.name = "ToolError";
  error.code = code;
  if (meta) {
    error.meta = meta;
  }
  // Validate error structure using Zod schema for early feedback.
  toolErrorSchema.parse({
    code,
    message: error.message,
    meta: error.meta,
    name: error.name,
    stack: error.stack,
  });
  return error;
}

/**
 * Check if an error is a ToolError.
 *
 * @param err Error to check.
 * @returns True if error has a recognized tool error code.
 */
export function isToolError(err: unknown): err is ToolError {
  if (!(err instanceof Error)) {
    return false;
  }
  const candidate = (err as ToolError).code;
  if (typeof candidate !== "string") {
    return false;
  }
  return (Object.values(TOOL_ERROR_CODES) as string[]).includes(candidate);
}
