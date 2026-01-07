/**
 * @fileoverview Canonical TanStack Query key factory.
 */

/**
 * Private query keys must be scoped by `userId` to prevent cross-user cache leakage.
 */
import type { TimeWindow } from "@schemas/dashboard";

type SearchSuggestionsType =
  | "flights"
  | "accommodations"
  | "activities"
  | "destinations";

export const keys = {
  // Agent Status & Monitoring (private)
  agents: {
    all: () => ["agents"] as const,
    status: (userId: string) => [...keys.agents.user(userId), "status"] as const,
    user: (userId: string) => [...keys.agents.all(), userId] as const,
    workflows: (userId: string) => [...keys.agents.user(userId), "workflows"] as const,
  },

  // Authentication & User Management (session scoped)
  auth: {
    all: () => ["auth"] as const,
    apiKeys: (userId: string) => [...keys.auth.all(), "api-keys", userId] as const,
    permissions: (userId: string) =>
      [...keys.auth.all(), "permissions", userId] as const,
    user: () => [...keys.auth.all(), "user"] as const,
    userId: () => [...keys.auth.user(), "id"] as const,
  },

  // Budget & Finance (private)
  budget: {
    alerts: (userId: string, budgetId: string) =>
      [...keys.budget.detail(userId, budgetId), "alerts"] as const,
    all: () => ["budget"] as const,
    analysis: (userId: string, tripId: number, timeframe?: string) =>
      [
        ...keys.budget.user(userId),
        "analysis",
        tripId,
        { timeframe: timeframe ?? null },
      ] as const,
    categories: (userId: string) =>
      [...keys.budget.user(userId), "categories"] as const,
    detail: (userId: string, budgetId: string) =>
      [...keys.budget.user(userId), "detail", budgetId] as const,
    expenses: (userId: string, budgetId: string) =>
      [...keys.budget.detail(userId, budgetId), "expenses"] as const,
    list: (userId: string) => [...keys.budget.user(userId), "list"] as const,
    trip: (userId: string, tripId: number) =>
      [...keys.budget.user(userId), "trip", tripId] as const,
    user: (userId: string) => [...keys.budget.all(), userId] as const,
  },

  // Calendar (private - user integrations)
  calendar: {
    all: () => ["calendar"] as const,
    events: (
      userId: string,
      params: {
        calendarId: string;
        timeMaxIso: string | null;
        timeMinIso: string | null;
      }
    ) => [...keys.calendar.user(userId), "events", params] as const,
    eventsDisabled: () => [...keys.calendar.all(), "events", "disabled"] as const,
    user: (userId: string) => [...keys.calendar.all(), userId] as const,
  },

  // Chat & Messages (private)
  chat: {
    all: () => ["chat"] as const,
    messages: (userId: string, sessionId: string) =>
      [...keys.chat.session(userId, sessionId), "messages"] as const,
    session: (userId: string, sessionId: string) =>
      [...keys.chat.sessions(userId), "session", sessionId] as const,
    sessionList: (userId: string, tripId?: number) =>
      [...keys.chat.sessions(userId), "list", { tripId: tripId ?? null }] as const,
    sessions: (userId: string) => [...keys.chat.user(userId), "sessions"] as const,
    stats: (userId: string) => [...keys.chat.user(userId), "stats"] as const,
    user: (userId: string) => [...keys.chat.all(), userId] as const,
  },

  // Currency (public external exchange rate data)
  currency: {
    all: () => ["currency"] as const,
    rate: (targetCurrency: string) =>
      [...keys.currency.all(), "rate", targetCurrency] as const,
    rates: () => [...keys.currency.all(), "rates"] as const,
  },

  // Dashboard & Metrics (private)
  dashboard: {
    all: () => ["dashboard"] as const,
    metrics: (userId: string, window?: TimeWindow) =>
      [...keys.dashboard.user(userId), "metrics", { window: window ?? null }] as const,
    metricsDisabled: () => [...keys.dashboard.all(), "metrics", "disabled"] as const,
    user: (userId: string) => [...keys.dashboard.all(), userId] as const,
  },

  // External API Data (public)
  external: {
    deals: (category?: string) =>
      ["external", "deals", { category: category ?? null }] as const,
    upcomingFlights: (params?: Record<string, unknown>) =>
      ["external", "upcoming-flights", { params: params ?? null }] as const,
  },

  // Files & Storage (private)
  files: {
    all: () => ["files"] as const,
    attachment: (userId: string, id: string) =>
      [...keys.files.user(userId), "attachment", id] as const,
    attachments: (userId: string, filters?: Record<string, unknown>) =>
      [
        ...keys.files.user(userId),
        "attachments",
        { filters: filters ?? null },
      ] as const,
    stats: (userId: string) => [...keys.files.user(userId), "stats"] as const,
    user: (userId: string) => [...keys.files.all(), userId] as const,
  },

  // Flights (public - discovery endpoints)
  flights: {
    all: () => ["flights"] as const,
    popularDestinations: () => [...keys.flights.all(), "popular-destinations"] as const,
    popularRoutes: () => [...keys.flights.all(), "popular-routes"] as const,
  },

  // Memory & Conversation Context (private)
  memory: {
    all: () => ["memory"] as const,
    context: (userId: string) => [...keys.memory.user(userId), "context"] as const,
    insights: (userId: string) => [...keys.memory.user(userId), "insights"] as const,
    search: (userId: string, searchParams?: string | Record<string, unknown>) =>
      [...keys.memory.user(userId), "search", searchParams ?? null] as const,
    stats: (userId: string) => [...keys.memory.user(userId), "stats"] as const,
    user: (userId: string) => [...keys.memory.all(), userId] as const,
  },

  // Supabase Real-time Subscriptions (private)
  realtime: {
    agents: (userId: string) => ["realtime", "agents", userId] as const,
    chat: (userId: string, sessionId: string) =>
      ["realtime", "chat", userId, sessionId] as const,
    trips: (userId: string) => ["realtime", "trips", userId] as const,
  },

  // Search & Discovery (private - authenticated experience)
  search: {
    accommodations: (userId: string, params: Record<string, unknown>) =>
      [...keys.search.user(userId), "accommodations", { params }] as const,
    activities: (userId: string, params: Record<string, unknown>) =>
      [...keys.search.user(userId), "activities", { params }] as const,
    all: () => ["search"] as const,
    destinations: (userId: string, params: Record<string, unknown>) =>
      [...keys.search.user(userId), "destinations", { params }] as const,
    flights: (userId: string, params: Record<string, unknown>) =>
      [...keys.search.user(userId), "flights", { params }] as const,
    suggestions: (userId: string, type: SearchSuggestionsType) =>
      [...keys.search.user(userId), "suggestions", type] as const,
    user: (userId: string) => [...keys.search.all(), userId] as const,
  },

  // Trips & Itineraries (private)
  trips: {
    all: () => ["trips"] as const,
    collaborators: (userId: string, tripId: number) =>
      [...keys.trips.detail(userId, tripId), "collaborators"] as const,
    collaboratorsDisabled: () =>
      [...keys.trips.all(), "collaborators", "disabled"] as const,
    detail: (userId: string, tripId: number) =>
      [...keys.trips.user(userId), "detail", tripId] as const,
    detailDisabled: () => [...keys.trips.all(), "detail", "disabled"] as const,
    itinerary: (userId: string, tripId: number) =>
      [...keys.trips.detail(userId, tripId), "itinerary"] as const,
    itineraryDisabled: () => [...keys.trips.all(), "itinerary", "disabled"] as const,
    list: (userId: string, filters?: Record<string, unknown>) =>
      [...keys.trips.lists(userId), { filters: filters ?? null }] as const,
    listDisabled: () => [...keys.trips.all(), "list", "disabled"] as const,
    lists: (userId: string) => [...keys.trips.user(userId), "list"] as const,
    suggestion: (userId: string, params?: Record<string, unknown>) =>
      [...keys.trips.suggestions(userId), { params: params ?? null }] as const,
    suggestions: (userId: string) =>
      [...keys.trips.user(userId), "suggestions"] as const,
    user: (userId: string) => [...keys.trips.all(), userId] as const,
  },
} as const;
