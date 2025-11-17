/**
 * @fileoverview Centralized rate limit registry for API routes.
 *
 * Single source of truth for route-level rate limit configurations across all
 * API routes. Used by withApiGuards factory. Per ADR-0032.
 *
 * Note: Agent tool-level rate limiting (within agent execution) is handled by
 * lib/ratelimit/config.ts. This registry is for HTTP route-level limits only.
 */

/**
 * Rate limit configuration.
 */
export interface RouteRateLimitDefinition {
  /** Maximum number of requests allowed per window. */
  limit: number;
  /** Time window string (e.g., "1 m", "1 h", "1 d"). */
  window: string;
}

/**
 * Rate limit registry for all API routes.
 *
 * Key format: `{namespace}:{resource}:{action}` (e.g., `agents:flight`,
 * `chat:sessions:list`, `calendar:events:read`).
 */
export const ROUTE_RATE_LIMITS = {
  "agents:accommodations": { limit: 30, window: "1 m" },
  "agents:budget": { limit: 30, window: "1 m" },
  "agents:destinations": { limit: 30, window: "1 m" },
  // Agent routes (already compliant)
  "agents:flight": { limit: 30, window: "1 m" },
  "agents:itineraries": { limit: 30, window: "1 m" },
  "agents:memory": { limit: 30, window: "1 m" },
  "agents:router": { limit: 100, window: "1 m" },
  "ai:stream": { limit: 40, window: "1 m" },
  "attachments:files": { limit: 20, window: "1 m" },
  "calendar:events:create": { limit: 10, window: "1 m" },
  "calendar:events:delete": { limit: 10, window: "1 m" },

  // Calendar events
  "calendar:events:read": { limit: 60, window: "1 m" },
  "calendar:events:update": { limit: 10, window: "1 m" },
  "calendar:freebusy": { limit: 60, window: "1 m" },
  "calendar:ics:export": { limit: 20, window: "1 m" },
  "calendar:ics:import": { limit: 10, window: "1 m" },
  "calendar:status": { limit: 60, window: "1 m" },
  "chat:attachments": { limit: 20, window: "1 m" },
  "chat:nonstream": { limit: 40, window: "1 m" },
  "chat:sessions:create": { limit: 30, window: "1 m" },
  "chat:sessions:delete": { limit: 20, window: "1 m" },
  "chat:sessions:get": { limit: 60, window: "1 m" },

  // Chat sessions
  "chat:sessions:list": { limit: 60, window: "1 m" },
  "chat:sessions:messages:create": { limit: 40, window: "1 m" },
  "chat:sessions:messages:list": { limit: 60, window: "1 m" },
  "chat:stream": { limit: 40, window: "1 m" },

  // Other routes
  embeddings: { limit: 60, window: "1 m" },
  geocode: { limit: 60, window: "1 m" },

  // Keys (BYOK routes - security sensitive)
  "keys:create": { limit: 10, window: "1 m" },
  "keys:delete": { limit: 20, window: "1 m" },
  "keys:validate": { limit: 20, window: "1 m" },
  "places:details": { limit: 60, window: "1 m" },
  "places:photo": { limit: 60, window: "1 m" },

  // Places & geocoding
  "places:search": { limit: 60, window: "1 m" },
  "route-matrix": { limit: 30, window: "1 m" },

  // Routes & directions
  routes: { limit: 60, window: "1 m" },
  "telemetry:ai-demo": { limit: 10, window: "1 m" },
  timezone: { limit: 60, window: "1 m" },

  // User settings
  "user-settings:get": { limit: 60, window: "1 m" },
  "user-settings:update": { limit: 10, window: "1 m" },
} as const satisfies Record<string, RouteRateLimitDefinition>;

/**
 * Type for rate limit registry keys.
 */
export type RouteRateLimitKey = keyof typeof ROUTE_RATE_LIMITS;
