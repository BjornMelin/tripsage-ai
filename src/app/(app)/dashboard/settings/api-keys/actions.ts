/**
 * @fileoverview Server Actions for user settings mutations.
 */

"use server";

import "server-only";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import type { Database } from "@/lib/supabase/database.types";
import { createServerSupabase, getCurrentUser } from "@/lib/supabase/server";

const gatewayFallbackPreferenceSchema = z.boolean({
  error: "allowGatewayFallback must be a boolean",
});

/**
 * Updates the user's gateway fallback preference setting.
 *
 * @param allowGatewayFallback - Whether to allow gateway fallback.
 */
export async function updateGatewayFallbackPreference(
  allowGatewayFallback: boolean
): Promise<Result<null, ResultError>> {
  const preferenceParse =
    gatewayFallbackPreferenceSchema.safeParse(allowGatewayFallback);
  if (!preferenceParse.success) {
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(preferenceParse.error),
      issues: preferenceParse.error.issues,
      reason: "Invalid gateway fallback preference",
    });
  }

  const supabase = await createServerSupabase();
  const { user } = await getCurrentUser(supabase);
  if (!user) {
    return err({
      error: "unauthorized",
      reason: "Unauthorized",
    });
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
    return err({
      error: "internal",
      reason: "Failed to update user settings",
    });
  }

  // Revalidate the settings page to reflect the change
  revalidatePath("/dashboard/settings/api-keys");

  return ok(null);
}
