/**
 * @fileoverview Browser Supabase client factory and React hook. Provides a singleton typed client for the Database schema.
 */

"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { useMemo } from "react";
import { getClientEnvVar } from "@/lib/env/client";
import type { Database } from "./database.types";

/** Type alias for Supabase client with Database schema. */
export type TypedSupabaseClient = SupabaseClient<Database>;

/** The browser singleton Supabase client. */
let client: TypedSupabaseClient | null = null;

const SSR_SUPABASE_CLIENT = new Proxy(
  {},
  {
    get(_target, prop) {
      const stack = new Error().stack;
      throw new Error(
        `Attempted to access Supabase client property "${String(prop)}" during SSR/prerender. ` +
          "This client is only available in the browser after component hydration. " +
          `Move Supabase operations into a useEffect hook or server action.\n\nCall stack:\n${stack}`
      );
    },
  }
) as TypedSupabaseClient;

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

  const supabaseUrl = getClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
  const supabaseAnonKey = getClientEnvVar("NEXT_PUBLIC_SUPABASE_ANON_KEY");

  // Allow the app to boot in dev/build placeholder mode without crashing.
  if (!supabaseUrl || !supabaseAnonKey) {
    if (process.env.NODE_ENV === "development") {
      console.warn(
        "[supabase/client] Supabase env vars missing (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY or NEXT_PUBLIC_SUPABASE_ANON_KEY). " +
          "This is expected during development or build with placeholder mode enabled."
      );
    }
    return null;
  }

  client = createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
  return client;
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
    if (typeof window === "undefined") {
      return SSR_SUPABASE_CLIENT;
    }
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

  const supabaseUrl = getClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
  const supabaseAnonKey = getClientEnvVar("NEXT_PUBLIC_SUPABASE_ANON_KEY");

  if (!supabaseUrl || !supabaseAnonKey) {
    return null;
  }

  // Intentionally create a fresh client (used by utility code that expects non-singleton behavior)
  return createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
}
