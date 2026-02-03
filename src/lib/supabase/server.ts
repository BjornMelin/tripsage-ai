/**
 * @fileoverview Server-only Supabase client entrypoint wired to Next.js cookies().
 */

import "server-only";

import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { cache } from "react";
import type { Database } from "./database.types";
import { createCookieAdapter, createServerSupabaseClient } from "./factory";

export type TypedServerSupabase = SupabaseClient<Database>;

const getServerSupabaseForCookies = cache(
  async (
    cookieStore: Awaited<ReturnType<typeof cookies>>
  ): Promise<TypedServerSupabase> =>
    createServerSupabaseClient({
      cookies: createCookieAdapter(cookieStore),
    })
);

/**
 * Creates server Supabase client with Next.js cookies.
 * @returns Promise resolving to typed Supabase server client
 */
export async function createServerSupabase(): Promise<TypedServerSupabase> {
  const cookieStore = await cookies();
  return getServerSupabaseForCookies(cookieStore);
}

// Re-export factory utilities
export { getCurrentUser } from "./factory";
