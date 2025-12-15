/**
 * @fileoverview Shared TanStack Query timing constants (milliseconds).
 */

/** Stale times for different query types (ms). */
export const staleTimes = {
  budget: 5 * 60 * 1000, // 5 minutes - budget data
  chat: 30 * 1000, // 30 seconds - conversation context
  currency: 60 * 60 * 1000, // 1 hour - exchange rates rarely change
  default: 5 * 60 * 1000, // 5 minutes - global fallback
  memory: 5 * 60 * 1000, // 5 minutes - user preferences
  trips: 2 * 60 * 1000, // 2 minutes - trip data
} as const;

/** Cache times for different retention periods (ms). */
export const cacheTimes = {
  long: 60 * 60 * 1000, // 1 hour
  medium: 10 * 60 * 1000, // 10 minutes
  short: 5 * 60 * 1000, // 5 minutes
} as const;
