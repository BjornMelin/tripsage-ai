/**
 * @fileoverview Centralized error taxonomy and helpers for tool execution.
 *
 * Provides standardized error codes and constructors to ensure consistent
 * error handling across all tools.
 */

// biome-ignore-file lint/style/useNamingConvention: Error code property names must match existing string literals used throughout codebase

/**
 * Tool error codes organized by category.
 *
 * Each tool namespace has its own error codes for clarity and observability.
 * Error code strings use snake_case to match existing codebase conventions.
 */
export const TOOL_ERROR_CODES = {
  accom_booking_session_required: "accom_booking_session_required",
  accom_details_failed: "accom_details_failed",
  accom_details_not_configured: "accom_details_not_configured",
  accom_details_not_found: "accom_details_not_found",
  accom_details_rate_limited: "accom_details_rate_limited",
  accom_details_timeout: "accom_details_timeout",
  accom_details_unauthorized: "accom_details_unauthorized",
  accom_search_failed: "accom_search_failed",

  // Accommodation errors
  accom_search_not_configured: "accom_search_not_configured",
  accom_search_payment_required: "accom_search_payment_required",
  accom_search_rate_limited: "accom_search_rate_limited",
  accom_search_timeout: "accom_search_timeout",
  accom_search_unauthorized: "accom_search_unauthorized",
  approval_backend_unavailable: "approval_backend_unavailable",
  approval_missing_session: "approval_missing_session",

  // Approval errors
  approval_required: "approval_required",
  web_search_error: "web_search_error",
  web_search_failed: "web_search_failed",
  // Web search errors
  web_search_not_configured: "web_search_not_configured",
  web_search_payment_required: "web_search_payment_required",
  web_search_rate_limited: "web_search_rate_limited",
  web_search_unauthorized: "web_search_unauthorized",
} as const;

/**
 * Type for tool error codes.
 */
export type ToolErrorCode = (typeof TOOL_ERROR_CODES)[keyof typeof TOOL_ERROR_CODES];

/**
 * Extended Error type with tool-specific metadata.
 */
export interface ToolError extends Error {
  code: ToolErrorCode;
  meta?: Record<string, unknown>;
}

/**
 * Create a standardized tool error.
 *
 * @param code - Error code from TOOL_ERROR_CODES.
 * @param message - Optional error message (defaults to code).
 * @param meta - Optional metadata for observability.
 * @returns ToolError instance.
 */
export function createToolError(
  code: ToolErrorCode,
  message?: string,
  meta?: Record<string, unknown>
): ToolError {
  const error = new Error(message ?? code) as ToolError;
  error.code = code;
  if (meta) {
    error.meta = meta;
  }
  return error;
}


/**
 * Check if an error is a ToolError.
 *
 * @param err - Error to check.
 * @returns True if error has a tool error code.
 */
export function isToolError(err: unknown): err is ToolError {
  return (
    err instanceof Error &&
    "code" in err &&
    typeof (err as ToolError).code === "string" &&
    Object.values(TOOL_ERROR_CODES).includes((err as ToolError).code as ToolErrorCode)
  );
}
