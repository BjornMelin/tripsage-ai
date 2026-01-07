/**
 * @fileoverview Canonical tool error helpers for AI tools.
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
// Accommodation errors
const ACCOMMODATION_ERROR_CODES = {
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
  accomSearchNotConfigured: "accom_search_not_configured",
  accomSearchPaymentRequired: "accom_search_payment_required",
  accomSearchRateLimited: "accom_search_rate_limited",
  accomSearchTimeout: "accom_search_timeout",
  accomSearchUnauthorized: "accom_search_unauthorized",
} as const;

// Approval errors
const APPROVAL_ERROR_CODES = {
  approvalBackendUnavailable: "approval_backend_unavailable",
  approvalMissingSession: "approval_missing_session",
  approvalRequired: "approval_required",
} as const;

// Flight errors
const FLIGHT_ERROR_CODES = {
  flightNotConfigured: "flight_not_configured",
  flightOfferFailed: "flight_offer_failed",
} as const;

// General tool errors
const GENERAL_TOOL_ERROR_CODES = {
  invalidOutput: "invalid_output",
  invalidParams: "invalid_params",
  memoryUnexpectedStream: "memory_unexpected_stream",
  toolExecutionFailed: "tool_execution_failed",
  toolRateLimited: "tool_rate_limited",
} as const;

// Places errors
const PLACES_ERROR_CODES = {
  placesDetailsFailed: "places_details_failed",
  placesDetailsNotFound: "places_details_not_found",
  placesNotConfigured: "places_not_configured",
  placesSearchFailed: "places_search_failed",
} as const;

// Trip errors
const TRIP_ERROR_CODES = {
  tripSavePlaceFailed: "trip_save_place_failed",
  tripSavePlaceUnauthorized: "trip_save_place_unauthorized",
} as const;

// Web search errors
const WEB_SEARCH_ERROR_CODES = {
  webSearchError: "web_search_error",
  webSearchFailed: "web_search_failed",
  webSearchNotConfigured: "web_search_not_configured",
  webSearchPaymentRequired: "web_search_payment_required",
  webSearchRateLimited: "web_search_rate_limited",
  webSearchUnauthorized: "web_search_unauthorized",
} as const;

export const TOOL_ERROR_CODES = {
  ...ACCOMMODATION_ERROR_CODES,
  ...APPROVAL_ERROR_CODES,
  ...FLIGHT_ERROR_CODES,
  ...GENERAL_TOOL_ERROR_CODES,
  ...PLACES_ERROR_CODES,
  ...TRIP_ERROR_CODES,
  ...WEB_SEARCH_ERROR_CODES,
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
