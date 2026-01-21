import { isTimeoutError } from "@/lib/api/error-types";
import { errorResponse } from "@/lib/api/route-helpers";

/**
 * Internal error codes for key validation and provider responses.
 */
export const PLANNED_ERROR_CODES = {
  invalidKey: "INVALID_KEY",
  networkError: "NETWORK_ERROR",
  requestTimeout: "REQUEST_TIMEOUT",
  vaultUnavailable: "VAULT_UNAVAILABLE",
} as const;

/**
 * Error code literal type for planned failure modes.
 */
export type PlannedErrorCode =
  (typeof PLANNED_ERROR_CODES)[keyof typeof PLANNED_ERROR_CODES];

/**
 * Creates a 500 Response indicating the Vault service is unavailable.
 *
 * @param reason - Detailed reason for the failure.
 * @param err - Optional underlying error object.
 * @returns Error response with VAULT_UNAVAILABLE code.
 */
export function vaultUnavailableResponse(reason: string, err?: unknown): Response {
  return errorResponse({
    err,
    error: PLANNED_ERROR_CODES.vaultUnavailable,
    reason,
    status: 500,
  });
}

/**
 * Maps an HTTP status code from a provider to a PlannedErrorCode.
 *
 * @param status - HTTP status code from the provider.
 * @returns Mapped error code (NETWORK_ERROR or INVALID_KEY).
 */
export function mapProviderStatusToCode(status: number): PlannedErrorCode {
  if (status === 429) return PLANNED_ERROR_CODES.networkError;
  if (status >= 500) return PLANNED_ERROR_CODES.networkError;
  if (status >= 400) return PLANNED_ERROR_CODES.invalidKey;
  return PLANNED_ERROR_CODES.networkError;
}

/**
 * Checks if an error is a timeout or abort-related exception.
 *
 * @param error - The error to check.
 * @returns True if the error is an AbortError or TimeoutError.
 */
function isAbortError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  if (isTimeoutError(error)) return true;
  const name = (error as { name?: unknown }).name;
  return name === "AbortError" || name === "TimeoutError";
}

/**
 * Maps a caught exception to a PlannedErrorCode.
 *
 * @param error - The exception to map.
 * @returns REQUEST_TIMEOUT for aborts/timeouts, otherwise NETWORK_ERROR.
 */
export function mapProviderExceptionToCode(error: unknown): PlannedErrorCode {
  if (isAbortError(error)) return PLANNED_ERROR_CODES.requestTimeout;
  return PLANNED_ERROR_CODES.networkError;
}
