import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { useMemo } from "react";
import type { Database } from "./database.types";

export type TypedSupabaseClient = SupabaseClient<Database>;

let client: TypedSupabaseClient | undefined;

/**
 * Create a singleton Supabase client for browser use
 * This ensures we only have one client instance throughout the app
 */
function getSupabaseBrowserClient(): TypedSupabaseClient {
  if (client) {
    return client;
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  }

  client = createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
  return client;
}

/**
 * React hook to get the Supabase client
 * Memoizes the client to prevent unnecessary re-renders
 */
export function useSupabase(): TypedSupabaseClient {
  return useMemo(getSupabaseBrowserClient, []);
}

/**
 * Create a new Supabase client instance (for special cases)
 * Use useSupabase() hook in components instead
 */
export function createClient(): TypedSupabaseClient {
  return getSupabaseBrowserClient();
}
