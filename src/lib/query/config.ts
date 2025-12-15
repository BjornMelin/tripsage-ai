/**
 * @fileoverview Shared TanStack Query timing constants (milliseconds).
 */

/** Stale times for different query types (ms). */
export const staleTimes = {
  // Core domains
  budget: 5 * 60 * 1000, // 5 minutes - budget data

  // App-wide feature groups
  categories: 60 * 60 * 1000, // 1 hour - typically stable reference data
  chat: 30 * 1000, // 30 seconds - conversation context
  configuration: 60 * 60 * 1000, // 1 hour - app/config data changes rarely
  currency: 60 * 60 * 1000, // 1 hour - exchange rates rarely change
  dashboard: 30 * 1000, // 30 seconds - fast-changing metrics
  default: 5 * 60 * 1000, // 5 minutes - global fallback
  files: 5 * 60 * 1000, // 5 minutes - attachment listings, etc.
  memory: 5 * 60 * 1000, // 5 minutes - user preferences
  realtime: 30 * 1000, // 30 seconds - realtime-adjacent computed data
  search: 2 * 60 * 1000, // 2 minutes - search results
  stats: 15 * 60 * 1000, // 15 minutes - derived aggregates
  suggestions: 15 * 60 * 1000, // 15 minutes - recommendations
  trips: 2 * 60 * 1000, // 2 minutes - trip data
  user: 5 * 60 * 1000, // 5 minutes - user/session scoped data
} as const;

/** Cache times for different retention periods (ms). */
export const cacheTimes = {
  long: 60 * 60 * 1000, // 1 hour
  medium: 10 * 60 * 1000, // 10 minutes
  short: 5 * 60 * 1000, // 5 minutes
} as const;
