/**
 * @fileoverview Server-only Supabase admin client factory using service role key.
 * Used exclusively by Next.js Route Handlers to call SECURITY DEFINER RPCs.
 */
import "server-only";

import type { SupabaseClient } from "@supabase/supabase-js";
import { createClient } from "@supabase/supabase-js";
import { getServerEnvVar } from "@/lib/env/server";
import type { Database } from "./database.types";

export type TypedAdminSupabase = SupabaseClient<Database>;

/**
 * Create an admin Supabase client authenticated with the service-role key.
 *
 * This client must only be used on the server (never bundled to the client)
 * and is intended for invoking SECURITY DEFINER functions and administrative
 * operations that require elevated privileges.
 *
 * @returns A typed Supabase admin client instance.
 * @throws Error when required environment variables are missing.
 */
export function createAdminSupabase(): TypedAdminSupabase {
  const supabaseUrl = getServerEnvVar("NEXT_PUBLIC_SUPABASE_URL");
  const serviceRoleKey = getServerEnvVar("SUPABASE_SERVICE_ROLE_KEY");

  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
    );
  }

  return createClient<Database>(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });
}

/** Cached singleton for reuse within a request lifecycle. */
let cachedAdminSupabase: TypedAdminSupabase | null = null;

/**
 * Returns a cached admin Supabase client, creating it if absent.
 *
 * Safe to use in server-only contexts; avoids per-call instantiation while
 * still honoring serverless re-instantiation on cold starts.
 */
export function getAdminSupabase(): TypedAdminSupabase {
  if (cachedAdminSupabase) {
    return cachedAdminSupabase;
  }
  cachedAdminSupabase = createAdminSupabase();
  return cachedAdminSupabase;
}
