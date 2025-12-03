/**
 * @fileoverview Shared formatting utilities for search feature.
 */

/**
 * Format a number as USD currency with no fractional digits.
 * 
 * @param value - The number to format.
 * @returns The formatted currency string.
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
    style: "currency",
  }).format(value);
}

/**
 * Convert a duration in hours (possibly fractional) to abbreviated format string.
 *
 * @param hours - The duration in hours to format.
 * Examples:
 * - 0.5 -> "30m"
 * - 1 -> "1h"
 * - 1.5 -> "1h 30m"
 * - 24 -> "24h"
 * - 26 -> "26h"
 *
 * @throws Error if hours is negative, NaN, or Infinity
 */
export function formatDurationHours(hours: number): string {
  if (!Number.isFinite(hours) || hours < 0) {
    throw new Error(
      `Invalid duration hours: ${hours}. Must be a non-negative finite number.`
    );
  }

  if (hours < 1) {
    const mins = Math.round(hours * 60);
    return `${mins}m`;
  }

  const wholeHours = Math.floor(hours);
  const mins = Math.round((hours - wholeHours) * 60);

  if (mins === 0) {
    return `${wholeHours}h`;
  }

  return `${wholeHours}h ${mins}m`;
}

/**
 * Convert minutes to `Xh Ym` representation.
 * 
 * @param minutes - The duration in minutes to format.
 * @returns The formatted duration string.
 */
export function formatDurationMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}
