/**
 * @fileoverview Server-only Supabase client entrypoint wired to Next.js cookies().
 */

import "server-only";

import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import type { Database } from "./database.types";
import { createCookieAdapter, createServerSupabaseClient } from "./factory";

export type TypedServerSupabase = SupabaseClient<Database>;

/**
 * Creates server Supabase client with Next.js cookies.
 * @returns Promise resolving to typed Supabase server client
 */
export async function createServerSupabase(): Promise<TypedServerSupabase> {
  const cookieStore = await cookies();
  return createServerSupabaseClient({
    cookies: createCookieAdapter(cookieStore),
  });
}

// Re-export factory utilities
export { getCurrentUser } from "./factory";
