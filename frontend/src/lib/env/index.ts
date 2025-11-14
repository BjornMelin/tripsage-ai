/**
 * @fileoverview Environment variable access module.
 *
 * This barrel file exports explicit server and client entrypoints.
 * Import from './server' for server-only access, './client' for client-safe access.
 *
 * DO NOT import from this index in client components - use explicit paths.
 */

// Client-safe exports
export {
  getClientEnv,
  getClientEnvVar,
  getClientEnvVarWithFallback,
  getGoogleMapsBrowserKey,
  publicEnv,
} from "./client";
// Explicit exports to prevent accidental wildcard imports
export type { ClientEnv, ServerEnv } from "./schema";
// Server-only exports (will fail if imported in client)
export {
  env as serverEnv,
  getGoogleMapsServerKey,
  getServerEnv,
  getServerEnvVar,
  getServerEnvVarWithFallback,
} from "./server";
