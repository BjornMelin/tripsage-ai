/**
 * @fileoverview Centralized application routes.
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
  faq: "/faq",

  // Root
  home: "/",
  // Auth routes
  login: "/login",

  // Legal routes
  privacy: "/privacy",
  register: "/register",

  // Search results
  searchFlightsResults: "/dashboard/search/flights/results",
  terms: "/terms",
} as const;
