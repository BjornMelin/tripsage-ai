/**
 * @fileoverview Browser/client-safe Supabase exports.
 *
 * Server entrypoints live in `./server` (Route Handlers / Server Components) and
 * `./factory` (middleware/proxy cookie adapters).
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
