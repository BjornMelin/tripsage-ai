/**
 * @fileoverview Centralized application routes.
 *
 * Provides a single source of truth for all internal routes to ensure
 * consistency across the application.
 */

export const ROUTES = {
  // Demo route
  aiDemo: "/ai-demo",

  // Chat
  chat: "/chat",
  contact: "/contact",

  // Dashboard routes
  dashboard: {
    agentStatus: "/dashboard/agent-status",
    billing: "/dashboard/billing",
    calendar: "/dashboard/calendar",
    profile: "/dashboard/profile",
    root: "/dashboard",
    search: "/dashboard/search",
    security: "/dashboard/security",
    settings: "/dashboard/settings",
    settingsApiKeys: "/dashboard/settings/api-keys",
    team: "/dashboard/team",
    trips: "/dashboard/trips",
  },

  // Root
  home: "/",
  // Auth routes
  login: "/login",

  // Legal routes
  privacy: "/privacy",
  register: "/register",

  // Search results
  searchFlightsResults: "/search/flights/results",
  terms: "/terms",
} as const;
