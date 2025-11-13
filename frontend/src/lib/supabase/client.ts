/**
 * @fileoverview Browser Supabase client factory and React hook.
 * Provides a singleton typed client for the Database schema.
 */
import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { useMemo } from "react";
import { getClientEnvVar } from "@/lib/env/client";
import type { Database } from "./database.types";

export type TypedSupabaseClient = SupabaseClient<Database>;

let client: TypedSupabaseClient | undefined;

/**
 * Return the browser singleton Supabase client.
 * Creates one instance on first call and reuses it throughout the app.
 * Exported so non-React modules (e.g., Zustand stores) can reuse the same
 * instance that the RealtimeAuthProvider authenticates.
 */
export function getBrowserClient(): TypedSupabaseClient {
  if (client) {
    return client;
  }

  try {
    const supabaseUrl = getClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
    const supabaseAnonKey = getClientEnvVar("NEXT_PUBLIC_SUPABASE_ANON_KEY");
    client = createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
    return client;
  } catch {
    // During SSR/prerender, avoid throwing to allow pages to build
    if (typeof window === "undefined") {
      return (client ?? ({} as unknown)) as TypedSupabaseClient;
    }
    throw new Error(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  }
}

/**
 * React hook to get the Supabase client
 * Memoizes the client to prevent unnecessary re-renders
 */
export function useSupabase(): TypedSupabaseClient {
  return useMemo(getBrowserClient, []);
}

/**
 * Create a new Supabase client instance (for special cases)
 * Use useSupabase() hook in components instead
 */
export function createClient(): TypedSupabaseClient {
  try {
    const supabaseUrl = getClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
    const supabaseAnonKey = getClientEnvVar("NEXT_PUBLIC_SUPABASE_ANON_KEY");
    // Intentionally create a fresh client (used by utility code that expects non-singleton behavior)
    return createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
  } catch {
    // For SSR/prerender safety, mimic the singleton behavior when missing envs
    if (typeof window === "undefined") {
      return {} as unknown as TypedSupabaseClient;
    }
    throw new Error(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  }
}
