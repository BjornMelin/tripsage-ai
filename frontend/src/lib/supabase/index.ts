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
export type {
  BrowserSupabaseClient,
  CreateServerSupabaseOptions,
  GetCurrentUserResult,
  ServerSupabaseClient,
} from "./factory";
export { isSupabaseClient } from "./guards";
// Server client and utilities
export {
  createServerSupabase,
  getCurrentUser,
  type TypedServerSupabase,
} from "./server";
