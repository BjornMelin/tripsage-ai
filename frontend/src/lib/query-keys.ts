/**
 * Query key factory for consistent caching patterns across the application
 * Following React Query v5 best practices for query key organization
 */

export const queryKeys = {
  // Authentication & User Management
  auth: {
    user: () => ["auth", "user"] as const,
    apiKeys: () => ["auth", "api-keys"] as const,
    permissions: (userId: string) => ["auth", "permissions", userId] as const,
  },

  // Trips & Itineraries
  trips: {
    all: () => ["trips"] as const,
    lists: () => [...queryKeys.trips.all(), "list"] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.trips.lists(), { filters }] as const,
    details: () => [...queryKeys.trips.all(), "detail"] as const,
    detail: (id: number) => [...queryKeys.trips.details(), id] as const,
    suggestions: (params?: Record<string, unknown>) =>
      [...queryKeys.trips.all(), "suggestions", { params }] as const,
    collaborators: (tripId: number) =>
      [...queryKeys.trips.detail(tripId), "collaborators"] as const,
  },

  // Chat & Messages
  chat: {
    all: () => ["chat"] as const,
    sessions: () => [...queryKeys.chat.all(), "sessions"] as const,
    sessionList: (tripId?: number) =>
      [...queryKeys.chat.sessions(), { tripId }] as const,
    session: (sessionId: string) =>
      [...queryKeys.chat.all(), "session", sessionId] as const,
    messages: (sessionId: string) =>
      [...queryKeys.chat.session(sessionId), "messages"] as const,
    stats: (userId: string) => [...queryKeys.chat.all(), "stats", userId] as const,
  },

  // Search & Discovery
  search: {
    all: () => ["search"] as const,
    flights: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "flights", { params }] as const,
    accommodations: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "accommodations", { params }] as const,
    activities: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "activities", { params }] as const,
    destinations: (params: Record<string, unknown>) =>
      [...queryKeys.search.all(), "destinations", { params }] as const,
    suggestions: (type: "flights" | "accommodations" | "activities" | "destinations") =>
      [...queryKeys.search.all(), "suggestions", type] as const,
  },

  // Files & Storage
  files: {
    all: () => ["files"] as const,
    attachments: (filters?: Record<string, unknown>) =>
      [...queryKeys.files.all(), "attachments", { filters }] as const,
    attachment: (id: string) => [...queryKeys.files.all(), "attachment", id] as const,
    stats: (userId: string) => [...queryKeys.files.all(), "stats", userId] as const,
  },

  // External API Data
  external: {
    upcomingFlights: (params?: Record<string, unknown>) =>
      ["external", "upcoming-flights", { params }] as const,
    currency: (from: string, to: string) => ["external", "currency", from, to] as const,
    deals: (category?: string) => ["external", "deals", { category }] as const,
  },

  // Supabase Real-time Subscriptions
  realtime: {
    trips: (userId: string) => ["realtime", "trips", userId] as const,
    chat: (sessionId: string) => ["realtime", "chat", sessionId] as const,
    agents: (userId: string) => ["realtime", "agents", userId] as const,
  },

  // Agent Status & Monitoring
  agents: {
    all: () => ["agents"] as const,
    status: (userId: string) => [...queryKeys.agents.all(), "status", userId] as const,
    workflows: (userId: string) =>
      [...queryKeys.agents.all(), "workflows", userId] as const,
  },

  // Budget & Finance
  budget: {
    trips: (tripId: number) => ["budget", "trip", tripId] as const,
    categories: () => ["budget", "categories"] as const,
    analysis: (tripId: number, timeframe?: string) =>
      ["budget", "analysis", tripId, { timeframe }] as const,
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
   * Check if two query keys share the same base
   */
  shareBase: (key1: readonly unknown[], key2: readonly unknown[]) =>
    queryKeyUtils.getBaseKey(key1) === queryKeyUtils.getBaseKey(key2),

  /**
   * Create invalidation patterns for specific entity types
   */
  invalidation: {
    allTrips: () => queryKeys.trips.all(),
    tripDetails: (tripId: number) => queryKeys.trips.detail(tripId),
    allChat: () => queryKeys.chat.all(),
    allSearch: () => queryKeys.search.all(),
    allFiles: () => queryKeys.files.all(),
  },
} as const;

/**
 * Type helpers for query keys
 */
export type QueryKey = typeof queryKeys;
export type QueryKeyPath = keyof QueryKey;

/**
 * Factory function for creating dynamic query keys with validation
 */
export function createQueryKey<T extends readonly unknown[]>(
  baseKey: string,
  params?: Record<string, unknown>
): T {
  const key: (string | Record<string, unknown>)[] = params
    ? [baseKey, params]
    : [baseKey];
  return key as unknown as T;
}

/**
 * Predefined stale times for different types of data
 */
export const staleTimes = {
  // Fast changing data
  realtime: 30 * 1000, // 30 seconds
  chat: 1 * 60 * 1000, // 1 minute
  search: 2 * 60 * 1000, // 2 minutes

  // Medium changing data
  trips: 5 * 60 * 1000, // 5 minutes
  files: 5 * 60 * 1000, // 5 minutes
  user: 5 * 60 * 1000, // 5 minutes

  // Slow changing data
  suggestions: 15 * 60 * 1000, // 15 minutes
  stats: 15 * 60 * 1000, // 15 minutes
  currency: 30 * 60 * 1000, // 30 minutes

  // Very stable data
  configuration: 60 * 60 * 1000, // 1 hour
  categories: 60 * 60 * 1000, // 1 hour
} as const;

/**
 * Cache time (gcTime) configurations
 */
export const cacheTimes = {
  short: 5 * 60 * 1000, // 5 minutes
  medium: 15 * 60 * 1000, // 15 minutes
  long: 30 * 60 * 1000, // 30 minutes
  veryLong: 60 * 60 * 1000, // 1 hour
} as const;
