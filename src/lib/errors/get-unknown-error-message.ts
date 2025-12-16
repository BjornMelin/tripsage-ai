/**
 * @fileoverview Error helpers for normalizing unknown failures.
 */

/**
 * Returns a human-readable message from an unknown error value.
 *
 * Prefer this for promise rejection reasons (e.g., from Promise.allSettled()).
 *
 * @param reason - The thrown/rejected value to extract a message from.
 * @param fallback - Optional fallback message when no error message is available.
 * @returns A trimmed message when present, otherwise the fallback string.
 */
function trimmedOrFallback(message: string, fallback: string): string {
  const trimmedMessage = message.trim();
  return trimmedMessage.length > 0 ? trimmedMessage : fallback;
}

/**
 * Returns a human-readable message from an unknown error value.
 *
 * @param reason - The thrown/rejected value to extract a message from.
 * @param fallback - Optional fallback message when no error message is available.
 * @returns A trimmed message when present, otherwise the fallback string.
 */
export function getUnknownErrorMessage(
  reason: unknown,
  fallback = "Unknown error"
): string {
  if (typeof reason === "string") {
    return trimmedOrFallback(reason, fallback);
  }
  if (reason instanceof Error) {
    return trimmedOrFallback(reason.message, fallback);
  }
  if (reason !== null && typeof reason === "object") {
    const message = (reason as { message?: unknown }).message;
    if (typeof message === "string") {
      return trimmedOrFallback(message, fallback);
    }
  }
  return fallback;
}
