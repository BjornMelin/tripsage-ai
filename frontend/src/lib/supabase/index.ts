/**
 * @fileoverview Supabase client exports.
 * Unified factory API for server and browser clients.
 *
 * Note: Server-only utilities (createCookieAdapter, createMiddlewareSupabase)
 * are not re-exported here to prevent client bundles from loading server-only
 * modules. Import them directly from ./factory or ./server when needed.
 */

// Admin client (server-only service-role access)
export { createAdminSupabase, type TypedAdminSupabase } from "./admin";

// Browser client helpers
export {
  createClient,
  getBrowserClient,
  type TypedSupabaseClient,
  useSupabase,
} from "./client";

// Shared types (type-only exports are safe)
export type {
  BrowserSupabaseClient,
  CreateServerSupabaseOptions,
  GetCurrentUserResult,
  ServerSupabaseClient,
} from "./factory";

// Runtime guards
export { isSupabaseClient } from "./guards";

// Server client entrypoint (Next.js cookies() wrapper)
// This re-export is safe because server.ts has "server-only" guard
export { createServerSupabase, type TypedServerSupabase } from "./server";
// getCurrentUser is re-exported from server.ts (which has server-only guard)
export { getCurrentUser } from "./server";
