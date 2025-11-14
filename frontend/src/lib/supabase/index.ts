/**
 * @fileoverview Supabase client exports.
 * Unified factory API for server and browser clients.
 */

// Admin client
export { createAdminSupabase, type TypedAdminSupabase } from "./admin";

// Browser client
export {
  createClient,
  getBrowserClient,
  type TypedSupabaseClient,
  useSupabase,
} from "./client";
// Factory utilities and types
export {
  type BrowserSupabaseClient,
  type CreateServerSupabaseOptions,
  createCookieAdapter,
  type GetCurrentUserResult,
  isSupabaseClient,
  type ServerSupabaseClient,
} from "./factory";
// Server client and utilities
export {
  createServerSupabase,
  getCurrentUser,
  type TypedServerSupabase,
} from "./server";
