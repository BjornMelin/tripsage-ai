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
 *
 * @property limit Maximum number of requests allowed per window.
 * @property window Time window string (e.g., "1 m", "1 h", "1 d").
 */
export interface RouteRateLimitDefinition {
  limit: number;
  window: string;
}

/**
 * Rate limit registry for all API routes.
 *
 * Key format: `{namespace}:{resource}:{action}` (e.g., `agents:flight`,
 * `chat:sessions:list`, `calendar:events:read`).
 */
export const ROUTE_RATE_LIMITS = {
  "activities:details": { limit: 30, window: "1 m" },

  // Activities
  "activities:search": { limit: 20, window: "1 m" },
  // Agent routes
  "agents:accommodations": { limit: 30, window: "1 m" },
  "agents:budget": { limit: 30, window: "1 m" },
  "agents:destinations": { limit: 30, window: "1 m" },
  "agents:flight": { limit: 30, window: "1 m" },
  "agents:itineraries": { limit: 30, window: "1 m" },
  "agents:memory": { limit: 30, window: "1 m" },
  "agents:router": { limit: 100, window: "1 m" },

  // AI routes
  "ai:stream": { limit: 40, window: "1 m" },

  // Attachments
  "attachments:files": { limit: 20, window: "1 m" },

  // Calendar routes
  "calendar:events:create": { limit: 10, window: "1 m" },
  "calendar:events:delete": { limit: 10, window: "1 m" },
  "calendar:events:read": { limit: 60, window: "1 m" },
  "calendar:events:update": { limit: 10, window: "1 m" },
  "calendar:freebusy": { limit: 60, window: "1 m" },
  "calendar:ics:export": { limit: 20, window: "1 m" },
  "calendar:ics:import": { limit: 10, window: "1 m" },
  "calendar:status": { limit: 60, window: "1 m" },

  // Chat routes
  "chat:attachments": { limit: 20, window: "1 m" },
  "chat:nonstream": { limit: 60, window: "1 m" },
  "chat:sessions:create": { limit: 30, window: "1 m" },
  "chat:sessions:delete": { limit: 20, window: "1 m" },
  "chat:sessions:get": { limit: 60, window: "1 m" },
  "chat:sessions:list": { limit: 60, window: "1 m" },
  "chat:sessions:messages:create": { limit: 40, window: "1 m" },
  "chat:sessions:messages:list": { limit: 60, window: "1 m" },
  "chat:stream": { limit: 40, window: "1 m" },
  // Configuration
  "config:agents:read": { limit: 60, window: "1 m" },
  "config:agents:rollback": { limit: 10, window: "1 m" },
  "config:agents:update": { limit: 20, window: "1 m" },
  "config:agents:versions": { limit: 60, window: "1 m" },

  // Dashboard
  "dashboard:metrics": { limit: 30, window: "1 m" },

  // Embeddings and geocoding
  embeddings: { limit: 60, window: "1 m" },

  // Flights
  "flights:popular-destinations": { limit: 60, window: "1 m" },
  geocode: { limit: 60, window: "1 m" },

  // Itineraries
  "itineraries:create": { limit: 30, window: "1 m" },
  "itineraries:list": { limit: 60, window: "1 m" },

  // Keys (BYOK routes - security sensitive)
  "keys:create": { limit: 10, window: "1 m" },
  "keys:delete": { limit: 20, window: "1 m" },
  "keys:validate": { limit: 20, window: "1 m" },

  // Memory
  "memory:context": { limit: 60, window: "1 m" },
  "memory:conversations": { limit: 30, window: "1 m" },
  "memory:delete": { limit: 10, window: "1 m" },
  "memory:insights": { limit: 30, window: "1 m" },
  "memory:preferences": { limit: 20, window: "1 m" },
  "memory:search": { limit: 60, window: "1 m" },
  "memory:stats": { limit: 30, window: "1 m" },
  "memory:sync": { limit: 60, window: "1 m" },

  // Places
  "places:details": { limit: 60, window: "1 m" },
  "places:photo": { limit: 60, window: "1 m" },
  "places:search": { limit: 60, window: "1 m" },

  // Routes and directions
  "route-matrix": { limit: 30, window: "1 m" },
  routes: { limit: 60, window: "1 m" },

  // Security
  "security:sessions:list": { limit: 20, window: "1 m" },
  "security:sessions:terminate": { limit: 10, window: "1 m" },

  // Telemetry
  "telemetry:ai-demo": { limit: 10, window: "1 m" },

  // Timezone
  timezone: { limit: 60, window: "1 m" },

  // Trips
  "trips:create": { limit: 30, window: "1 m" },
  "trips:list": { limit: 60, window: "1 m" },
  "trips:suggestions": { limit: 30, window: "1 m" },

  // User settings
  "user-settings:get": { limit: 60, window: "1 m" },
  "user-settings:update": { limit: 10, window: "1 m" },
} as const satisfies Record<string, RouteRateLimitDefinition>;

/** Type for rate limit registry keys. */
export type RouteRateLimitKey = keyof typeof ROUTE_RATE_LIMITS;
