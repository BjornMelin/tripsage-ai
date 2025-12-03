/**
 * @fileoverview Shared formatting utilities for search feature.
 */

/**
 * Format a number as USD currency with no fractional digits.
 *
 * @param value - The number to format.
 * @returns The formatted currency string.
 */
export function formatCurrency(
  value: number,
  currency = "USD",
  locale = "en-US"
): string {
  return new Intl.NumberFormat(locale, {
    currency,
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
    style: "currency",
  }).format(value);
}

/**
 * Convert duration in hours to human-friendly text matching search UI tests.
 *
 * Rules:
 * - < 1 hour: round to minutes, e.g., 0.5 -> "30 mins"
 * - = 1 hour: "1 hour"
 * - < 24 hours: show one decimal at most, e.g., 2.5 -> "2.5 hours"
 * - >= 24 hours:
 *     * exact days => "N days"
 *     * otherwise => "Xd Yh" where Y is whole hours remainder
 */
export function formatDurationHours(hours: number): string {
  if (!Number.isFinite(hours) || hours < 0) {
    throw new Error(`Invalid duration hours: ${hours}. Must be non-negative finite.`);
  }

  if (hours < 1) {
    return `${Math.round(hours * 60)} mins`;
  }

  if (hours === 1) {
    return "1 hour";
  }

  if (hours < 24) {
    const rounded = Number.parseFloat(hours.toFixed(1));
    return `${rounded} hours`;
  }

  const days = Math.floor(hours / 24);
  const remainderHours = Math.floor(hours - days * 24);

  if (remainderHours === 0) {
    return `${days} ${days === 1 ? "day" : "days"}`;
  }

  return `${days}d ${remainderHours}h`;
}

/**
 * Convert minutes to `Xh Ym` representation.
 *
 * @param minutes - The duration in minutes to format.
 * @returns The formatted duration string.
 */
export function formatDurationMinutes(minutes: number): string {
  if (!Number.isFinite(minutes) || minutes < 0) {
    throw new Error(
      `Invalid duration minutes: ${minutes}. Must be non-negative finite.`
    );
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}
