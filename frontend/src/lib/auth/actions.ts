/**
 * @fileoverview Server actions for authentication.
 */

"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("auth.actions");

/**
 * Signs the user out and redirects to the login page.
 */
export async function logoutAction(): Promise<never> {
  const supabase = await createServerSupabase();
  try {
    await supabase.auth.signOut();
  } catch (error) {
    logger.error("Logout error", { error });
  }
  revalidatePath("/");
  redirect("/login");
}
