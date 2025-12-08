/**
 * @fileoverview Server Actions for user settings mutations.
 */

"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { Database } from "@/lib/supabase/database.types";
import { createServerSupabase, getCurrentUser } from "@/lib/supabase/server";

/**
 * Updates the user's gateway fallback preference setting.
 *
 * @param allowGatewayFallback - Whether to allow gateway fallback.
 */
export async function updateGatewayFallbackPreference(
  allowGatewayFallback: boolean
): Promise<void> {
  const supabase = await createServerSupabase();
  const { user } = await getCurrentUser(supabase);
  if (!user) {
    redirect("/login");
  }

  // Upsert row with owner RLS via SSR client
  type UserSettingsInsert = Database["public"]["Tables"]["user_settings"]["Insert"];
  // DB column names use snake_case by convention
  const payload: UserSettingsInsert = {
    // biome-ignore lint/style/useNamingConvention: DB columns are snake_case
    allow_gateway_fallback: allowGatewayFallback,
    // biome-ignore lint/style/useNamingConvention: DB columns are snake_case
    user_id: user.id,
  };

  const { error: upsertError } = await supabase.from("user_settings").upsert(payload, {
    onConflict: "user_id",
  });

  if (upsertError) {
    throw new Error(`Failed to update user settings: ${upsertError.message}`);
  }

  // Revalidate the settings page to reflect the change
  revalidatePath("/settings/api-keys");
}
