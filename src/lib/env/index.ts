/**
 * @fileoverview Environment variable access module.
 */

// Client-safe exports
export {
  getClientEnv,
  getClientEnvVar,
  getClientEnvVarWithFallback,
  getGoogleMapsBrowserKey,
  publicEnv,
} from "./client";
// Server-only exports (will fail if imported in client)
export {
  env as serverEnv,
  getGoogleMapsServerKey,
  getServerEnv,
  getServerEnvVar,
  getServerEnvVarWithFallback,
} from "./server";
