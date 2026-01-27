/**
 * @fileoverview Shared helper to normalize error messages.
 */

/**
 * Extract a message string from an unknown error value.
 *
 * @param error - Error-like value to normalize.
 * @returns A string message for logging or diagnostics.
 */
export function extractErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
