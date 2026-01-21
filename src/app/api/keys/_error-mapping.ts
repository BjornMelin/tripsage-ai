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
 * Map a provider HTTP status code to a PlannedErrorCode.
 *
 * 429 and any status >= 500 map to `NETWORK_ERROR`; statuses from 400 through
 * 499 map to `INVALID_KEY`; all other statuses map to `NETWORK_ERROR`.
 *
 * @param status - HTTP status code returned by the provider
 * @returns The corresponding planned error code (`INVALID_KEY` or `NETWORK_ERROR`)
 */
export function mapProviderStatusToCode(status: number): PlannedErrorCode {
  if (status === 429) return PLANNED_ERROR_CODES.networkError;
  if (status >= 500) return PLANNED_ERROR_CODES.networkError;
  if (status >= 400) return PLANNED_ERROR_CODES.invalidKey;
  return PLANNED_ERROR_CODES.networkError;
}

/**
 * Determine whether an error represents an abort or timeout condition.
 *
 * @param error - The value to inspect for abort/timeout semantics.
 * @returns `true` if the error is an `AbortError` or `TimeoutError`, `false` otherwise.
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
