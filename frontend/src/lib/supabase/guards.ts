/**
 * @fileoverview Shared Supabase client utilities that are safe for any runtime.
 */

import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "./database.types";

type SupabaseAuthApi = SupabaseClient<Database>["auth"];

/**
 * Narrowly determines whether the provided value looks like a Supabase client.
 *
 * The check intentionally validates a few core APIs (auth/from/channel) instead
 * of relying on duck-typing a single property, which produced false positives.
 */
export function isSupabaseClient(client: unknown): client is SupabaseClient<Database> {
  if (typeof client !== "object" || client === null) {
    return false;
  }

  const candidate = client as Partial<SupabaseClient<Database>>;
  const auth = candidate.auth as SupabaseAuthApi | undefined;

  const hasAuthApi =
    typeof auth === "object" &&
    auth !== null &&
    typeof auth.getUser === "function" &&
    typeof auth.getSession === "function" &&
    typeof auth.onAuthStateChange === "function";

  const hasQueryBuilders =
    typeof candidate.from === "function" && typeof candidate.channel === "function";

  return Boolean(hasAuthApi && hasQueryBuilders);
}
