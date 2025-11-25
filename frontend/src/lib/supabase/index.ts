/**
 * @fileoverview Supabase client exports for browser/client-side usage.
 *
 * Note: Server-only utilities (createCookieAdapter, createMiddlewareSupabase,
 * createAdminSupabase, createServerSupabase, getCurrentUser) are not re-exported
 * here to prevent client bundles from loading server-only modules.
 * Import them directly from ./factory, ./server, or ./admin when needed in
 * server-side code (Route Handlers, Server Components, Server Actions).
 */

// Browser client helpers
export {
  createClient,
  getBrowserClient,
  type TypedSupabaseClient,
  useSupabase,
  useSupabaseRequired,
} from "./client";

// Shared types (type-only exports are safe - they don't cause server-only imports)
export type {
  BrowserSupabaseClient,
  CreateServerSupabaseOptions,
  GetCurrentUserResult,
  ServerSupabaseClient,
} from "./factory";

// Runtime guards
export { isSupabaseClient } from "./guards";
