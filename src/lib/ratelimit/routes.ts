/**
 * @fileoverview Centralized rate limit registry for API routes.
 */

import type { DegradedMode } from "./upstash";

/** Rate limit configuration for an API route. */
export interface RouteRateLimitDefinition {
  /** Behavior when Redis/rate-limit enforcement is unavailable. */
  degradedMode?: DegradedMode;
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
  // Accommodations
  "accommodations:personalize": {
    degradedMode: "fail_closed",
    limit: 10,
    window: "1 m",
  },
  "accommodations:popular-destinations": {
    degradedMode: "fail_closed",
    limit: 30,
    window: "1 m",
  },
  "accommodations:search": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "activities:details": { degradedMode: "fail_closed", limit: 30, window: "1 m" },

  // Activities
  "activities:search": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  // Agent routes
  "agents:accommodations": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "agents:budget": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "agents:destinations": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "agents:flight": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "agents:itineraries": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "agents:memory": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "agents:router": { degradedMode: "fail_closed", limit: 100, window: "1 m" },

  // AI routes
  "ai:stream": { degradedMode: "fail_closed", limit: 40, window: "1 m" },

  // Attachments
  "attachments:files": { limit: 20, window: "1 m" },

  // Auth (security-sensitive - tighter limits aligned with security best practices)
  "auth:login": { degradedMode: "fail_closed", limit: 5, window: "1 m" },
  "auth:mfa:backup:regenerate": {
    degradedMode: "fail_closed",
    limit: 3,
    window: "1 h",
  },
  "auth:mfa:backup:verify": { degradedMode: "fail_closed", limit: 3, window: "1 m" },
  "auth:mfa:challenge": { degradedMode: "fail_closed", limit: 3, window: "1 m" },
  "auth:mfa:factors:list": { degradedMode: "fail_closed", limit: 5, window: "1 m" },
  "auth:mfa:sessions:revoke": { degradedMode: "fail_closed", limit: 5, window: "10 m" },
  "auth:mfa:setup": { degradedMode: "fail_closed", limit: 3, window: "1 m" },
  "auth:mfa:verify": { degradedMode: "fail_closed", limit: 3, window: "1 m" },
  "auth:password:change": { degradedMode: "fail_closed", limit: 3, window: "10 m" },
  "auth:password:reset-request": {
    degradedMode: "fail_closed",
    limit: 5,
    window: "10 m",
  },
  "auth:register": { degradedMode: "fail_closed", limit: 3, window: "10 m" },

  // Calendar routes
  "calendar:events:create": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "calendar:events:delete": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "calendar:events:read": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "calendar:events:update": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "calendar:freebusy": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "calendar:ics:export": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "calendar:ics:import": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "calendar:status": { degradedMode: "fail_closed", limit: 60, window: "1 m" },

  // Chat routes
  "chat:attachments": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "chat:nonstream": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "chat:sessions:create": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "chat:sessions:delete": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "chat:sessions:get": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "chat:sessions:list": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "chat:sessions:messages:create": {
    degradedMode: "fail_closed",
    limit: 40,
    window: "1 m",
  },
  "chat:sessions:messages:list": {
    degradedMode: "fail_closed",
    limit: 60,
    window: "1 m",
  },
  "chat:stream": { degradedMode: "fail_closed", limit: 40, window: "1 m" },
  // Configuration
  "config:agents:read": { limit: 60, window: "1 m" },
  "config:agents:rollback": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "config:agents:update": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "config:agents:versions": { limit: 60, window: "1 m" },

  // Dashboard
  "dashboard:metrics": { limit: 30, window: "1 m" },

  // Embeddings and geocoding
  embeddings: { degradedMode: "fail_closed", limit: 60, window: "1 m" },

  // Flights
  "flights:popular-destinations": {
    degradedMode: "fail_closed",
    limit: 60,
    window: "1 m",
  },
  "flights:popular-routes": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "flights:search": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "flights:upcoming": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  geocode: { limit: 60, window: "1 m" },

  // Images
  "images:proxy": { limit: 60, window: "1 m" },

  // Itineraries
  "itineraries:create": { limit: 30, window: "1 m" },
  "itineraries:list": { limit: 60, window: "1 m" },

  // Keys (BYOK routes - security sensitive)
  "keys:create": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "keys:delete": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "keys:validate": { degradedMode: "fail_closed", limit: 20, window: "1 m" },

  // Memory
  "memory:context": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "memory:conversations": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "memory:delete": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "memory:insights": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "memory:preferences": { degradedMode: "fail_closed", limit: 20, window: "1 m" },
  "memory:search": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "memory:stats": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "memory:sync": { degradedMode: "fail_closed", limit: 60, window: "1 m" },

  // Places
  "places:details": { limit: 60, window: "1 m" },
  "places:nearby": { limit: 60, window: "1 m" },
  "places:photo": { limit: 60, window: "1 m" },
  "places:search": { limit: 60, window: "1 m" },

  // RAG (Retrieval-Augmented Generation)
  "rag:index": { limit: 10, window: "1 m" }, // Batch indexing
  "rag:search": { limit: 100, window: "1 m" }, // Hybrid search

  // Routes and directions
  "route-matrix": { limit: 30, window: "1 m" },
  routes: { limit: 60, window: "1 m" },

  // Security
  "security:csp-report": {
    degradedMode: "fail_open",
    limit: 120,
    window: "1 m",
  },
  "security:events": { limit: 20, window: "1 m" },
  "security:metrics": { limit: 20, window: "1 m" },
  "security:sessions:list": { limit: 20, window: "1 m" },
  "security:sessions:terminate": {
    degradedMode: "fail_closed",
    limit: 10,
    window: "1 m",
  },

  // Telemetry
  "telemetry:ai-demo": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "telemetry:post": { degradedMode: "fail_open", limit: 60, window: "1 m" },

  // Timezone
  timezone: { limit: 60, window: "1 m" },

  // Trips
  "trips:collaborators:invite": {
    degradedMode: "fail_closed",
    limit: 10,
    window: "1 m",
  },
  "trips:collaborators:list": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "trips:collaborators:remove": {
    degradedMode: "fail_closed",
    limit: 20,
    window: "1 m",
  },
  "trips:collaborators:update": {
    degradedMode: "fail_closed",
    limit: 20,
    window: "1 m",
  },
  "trips:create": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "trips:delete": { degradedMode: "fail_closed", limit: 10, window: "1 m" },
  "trips:detail": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "trips:list": { degradedMode: "fail_closed", limit: 60, window: "1 m" },
  "trips:suggestions": { degradedMode: "fail_closed", limit: 30, window: "1 m" },
  "trips:update": { degradedMode: "fail_closed", limit: 30, window: "1 m" },

  // User settings
  "user-settings:get": { limit: 60, window: "1 m" },
  "user-settings:update": { limit: 10, window: "1 m" },
} as const satisfies Record<string, RouteRateLimitDefinition>;

/** Type for rate limit registry keys. */
export type RouteRateLimitKey = keyof typeof ROUTE_RATE_LIMITS;

/**
 * Resolves the degraded-mode policy for a rate-limited route.
 *
 * @param key - Route rate-limit registry key.
 * @returns The configured policy, defaulting to fail-closed when unset.
 */
export function getRouteRateLimitDegradedMode(key: RouteRateLimitKey): DegradedMode {
  const config: RouteRateLimitDefinition = ROUTE_RATE_LIMITS[key];
  return config.degradedMode ?? "fail_closed";
}
