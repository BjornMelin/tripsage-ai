/**
 * @fileoverview Standardized API error response helper.
 */

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
