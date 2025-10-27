/**
 * Access token helper for Supabase session.
 *
 * Provides a single source of truth for acquiring the current
 * supabase-js session access token on the client.
 */
import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * Get the current access token from a Supabase client.
 *
 * @param supabase Supabase browser client
 * @returns access token string or null when unauthenticated
 */
export async function getAccessToken(
  supabase: SupabaseClient,
): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

