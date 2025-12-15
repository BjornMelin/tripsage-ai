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
export function getErrorMessage(reason: unknown, fallback = "Unknown error"): string {
  if (typeof reason === "string") {
    const trimmedMessage = reason.trim();
    return trimmedMessage.length > 0 ? trimmedMessage : fallback;
  }
  if (reason instanceof Error) {
    const trimmedMessage = reason.message.trim();
    return trimmedMessage.length > 0 ? trimmedMessage : fallback;
  }
  if (reason !== null && typeof reason === "object") {
    let message: unknown;
    try {
      message = (reason as { message?: unknown }).message;
    } catch {
      return fallback;
    }
    if (typeof message === "string") {
      const trimmedMessage = message.trim();
      return trimmedMessage.length > 0 ? trimmedMessage : fallback;
    }
  }
  return fallback;
}
