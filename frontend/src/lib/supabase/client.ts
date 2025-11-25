/**
 * @fileoverview Browser Supabase client factory and React hook.
 * Provides a singleton typed client for the Database schema.
 */

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { useMemo } from "react";
import { getClientEnvVar } from "@/lib/env/client";
import type { Database } from "./database.types";

/** Type alias for Supabase client with Database schema. */
export type TypedSupabaseClient = SupabaseClient<Database>;

/** The browser singleton Supabase client. */
let client: TypedSupabaseClient | null = null;

/**
 * Return the browser singleton Supabase client.
 * Instantiated once and reused across the app, including non-React modules
 * (e.g., Zustand stores) that share the authenticated instance.
 * 
 * @returns The browser singleton Supabase client.
 */
export function getBrowserClient(): TypedSupabaseClient | null {
  if (client) {
    return client;
  }

  // During SSR/prerender, return null to signal client unavailability
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const supabaseUrl = getClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
    const supabaseAnonKey = getClientEnvVar("NEXT_PUBLIC_SUPABASE_ANON_KEY");
    client = createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
    return client;
  } catch {
    throw new Error(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  }
}

/**
 * React hook to get the Supabase client.
 * Memoizes the client to prevent unnecessary re-renders.
 *
 * @returns The browser singleton Supabase client. Returns null during SSR.
 *   For hooks that require a non-null client, use {@link useSupabaseRequired} instead.
 */
export function useSupabase(): TypedSupabaseClient | null {
  return useMemo(getBrowserClient, []);
}

/**
 * React hook that returns a Supabase client, throwing if unavailable.
 *
 * Throws during SSR (window undefined) or if Supabase environment variables are missing.
 * Use only in client components after hydration.
 *
 * @throws Error if Supabase client cannot be initialized.
 */
export function useSupabaseRequired(): TypedSupabaseClient {
  const client = useMemo(getBrowserClient, []);
  if (!client) {
    throw new Error(
      "useSupabaseRequired: Supabase client unavailable. This hook can only be used in client components after hydration."
    );
  }
  return client;
}

/**
 * Create a new Supabase client instance (for special cases)
 * Use useSupabase() hook in components instead
 */
export function createClient(): TypedSupabaseClient | null {
  // During SSR/prerender, return null to signal client unavailability
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const supabaseUrl = getClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
    const supabaseAnonKey = getClientEnvVar("NEXT_PUBLIC_SUPABASE_ANON_KEY");
    // Intentionally create a fresh client (used by utility code that expects non-singleton behavior)
    return createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
  } catch {
    throw new Error(
      "Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  }
}
