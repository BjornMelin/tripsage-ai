/**
 * @fileoverview Server-only Supabase admin client factory using service role key.
 * Used exclusively by Next.js Route Handlers to call SECURITY DEFINER RPCs.
 */
import "server-only";

import type { SupabaseClient } from "@supabase/supabase-js";
import { createClient } from "@supabase/supabase-js";
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
  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error(
      "Missing Supabase environment variables. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
    );
  }

  return createClient<Database>(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });
}
