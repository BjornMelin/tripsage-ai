/**
 * @fileoverview Query key factory for consistent caching patterns across the application. Follows React Query v5 key composition guidance.
 */

import type { TimeWindow } from "@schemas/dashboard";

export const queryKeys = {
  // Agent Status & Monitoring
  agents: {
    all: () => ["agents"] as const,
    status: (userId: string) => [...queryKeys.agents.all(), "status", userId] as const,
    workflows: (userId: string) =>
      [...queryKeys.agents.all(), "workflows", userId] as const,
  },
  // Authentication & User Management
  auth: {
    apiKeys: () => ["auth", "api-keys"] as const,
    permissions: (userId: string) => ["auth", "permissions", userId] as const,
    user: () => ["auth", "user"] as const,
  },

  // Budget & Finance
  budget: {
    analysis: (tripId: number, timeframe?: string) =>
      ["budget", "analysis", tripId, { timeframe }] as const,
    categories: () => ["budget", "categories"] as const,
    trips: (tripId: number) => ["budget", "trip", tripId] as const,
  },

  // Chat & Messages
  chat: {
    all: () => ["chat"] as const,
    messages: (sessionId: string) =>
      [...queryKeys.chat.session(sessionId), "messages"] as const,
    session: (sessionId: string) =>
      [...queryKeys.chat.all(), "session", sessionId] as const,
    sessionList: (tripId?: number) =>
      [...queryKeys.chat.sessions(), { tripId }] as const,
    sessions: () => [...queryKeys.chat.all(), "sessions"] as const,
    stats: (userId: string) => [...queryKeys.chat.all(), "stats", userId] as const,
  },

  // Currency (external exchange rate data)
  currency: {
    all: () => ["currency"] as const,
    rate: (targetCurrency: string) =>
      [...queryKeys.currency.all(), "rate", targetCurrency] as const,
    rates: () => [...queryKeys.currency.all(), "rates"] as const,
  },

  // Dashboard & Metrics
  dashboard: {
    all: () => ["dashboard"] as const,
    metrics: (window?: TimeWindow) =>
      [...queryKeys.dashboard.all(), "metrics", { window }] as const,
  },

  // External API Data
  external: {
    deals: (category?: string) => ["external", "deals", { category }] as const,
    upcomingFlights: (params?: Record<string, unknown>) =>
      ["external", "upcoming-flights", { params }] as const,
  },

  // Files & Storage
  files: {
    all: () => ["files"] as const,
    attachment: (id: string) => [...queryKeys.files.all(), "attachment", id] as const,
    attachments: (filters?: Record<string, unknown>) =>
      [...queryKeys.files.all(), "attachments", { filters }] as const,
    stats: (userId: string) => [...queryKeys.files.all(), "stats", userId] as const,
  },

  // Memory & Conversation Context
  memory: {
    all: () => ["memory"] as const,
    context: (userId: string) =>
      [...queryKeys.memory.all(), "context", userId] as const,
    insights: (userId: string) =>
      [...queryKeys.memory.all(), "insights", userId] as const,
    search: (userId: string, searchParams?: string | Record<string, unknown>) =>
      [...queryKeys.memory.all(), "search", userId, searchParams ?? null] as const,
    stats: (userId: string) => [...queryKeys.memory.all(), "stats", userId] as const,
  },

  // Supabase Real-time Subscriptions
  realtime: {
    agents: (userId: string) => ["realtime", "agents", userId] as const,
    chat: (sessionId: string) => ["realtime", "chat", sessionId] as const,
    trips: (userId: string) => ["realtime", "trips", userId] as const,
  },

  // Search & Discovery
  search: {
    accommodations: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "accommodations", { params }] as const,
    activities: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "activities", { params }] as const,
    all: () => ["search"] as const,
    destinations: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "destinations", { params }] as const,
    flights: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "flights", { params }] as const,
    suggestions: (type: "flights" | "accommodations" | "activities" | "destinations") =>
      [...queryKeys.search.all(), "suggestions", type] as const,
  },

  // Trips & Itineraries
  trips: {
    all: () => ["trips"] as const,
    collaborators: (tripId: number) =>
      [...queryKeys.trips.detail(tripId), "collaborators"] as const,
    detail: (id: number) => [...queryKeys.trips.details(), id] as const,
    details: () => [...queryKeys.trips.all(), "detail"] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.trips.lists(), { filters }] as const,
    lists: () => [...queryKeys.trips.all(), "list"] as const,
    suggestions: (params?: Record<string, unknown>) =>
      [...queryKeys.trips.all(), "suggestions", { params }] as const,
  },
} as const;

/**
 * Utility functions for query key manipulation
 */
export const queryKeyUtils = {
  /**
   * Extract the base key from a query key for invalidation patterns
   */
  getBaseKey: (queryKey: readonly unknown[]) => queryKey[0] as string,

  /**
   * Create invalidation patterns for specific entity types
   */
  invalidation: {
    allChat: () => queryKeys.chat.all(),
    allFiles: () => queryKeys.files.all(),
    allSearch: () => queryKeys.search.all(),
    allTrips: () => queryKeys.trips.all(),
    tripDetails: (tripId: number) => queryKeys.trips.detail(tripId),
  },

  /**
   * Check if two query keys share the same base
   */
  shareBase: (key1: readonly unknown[], key2: readonly unknown[]) =>
    queryKeyUtils.getBaseKey(key1) === queryKeyUtils.getBaseKey(key2),
} as const;

/**
 * Type helpers for query keys
 */
export type QueryKey = typeof queryKeys;
export type QueryKeyPath = keyof QueryKey;

/**
 * Builds dynamic query key tuples.
 * @param baseKey - Base key string
 * @param params - Optional parameters object
 * @returns `[key]` or `[key, params]` depending on whether params are provided
 */
export function createQueryKey(
  baseKey: string,
  params?: Record<string, unknown>
): readonly [string] | readonly [string, Record<string, unknown>] {
  if (params) {
    return [baseKey, params];
  }
  return [baseKey];
}
