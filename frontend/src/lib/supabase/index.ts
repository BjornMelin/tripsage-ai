/**
 * @fileoverview Supabase client exports.
 * Unified factory API for server and browser clients.
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

// Unified factory utilities and types (server + middleware)
export type {
  BrowserSupabaseClient,
  CreateServerSupabaseOptions,
  GetCurrentUserResult,
  ServerSupabaseClient,
} from "./factory";
export {
  createCookieAdapter,
  createMiddlewareSupabase,
  getCurrentUser,
} from "./factory";

// Runtime guards
export { isSupabaseClient } from "./guards";

// Server client entrypoint (Next.js cookies() wrapper)
export { createServerSupabase, type TypedServerSupabase } from "./server";
