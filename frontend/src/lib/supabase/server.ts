/**
 * @fileoverview Server-side Supabase client creation.
 * Provides async wrapper for Next.js cookie integration.
 */

import "server-only";

import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import type { Database } from "./database.types";
import {
  createCookieAdapter,
  createServerSupabase as createSupabaseFactory,
} from "./factory";

export type TypedServerSupabase = SupabaseClient<Database>;

/**
 * Creates server Supabase client with Next.js cookies.
 * @returns Promise resolving to typed Supabase server client
 */
export async function createServerSupabase(): Promise<TypedServerSupabase> {
  const cookieStore = await cookies();
  return createSupabaseFactory({
    cookies: createCookieAdapter(cookieStore),
    enableTracing: true,
  });
}

// Re-export factory utilities
export { getCurrentUser } from "./factory";
