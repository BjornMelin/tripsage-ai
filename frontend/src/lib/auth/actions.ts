/**
 * @fileoverview Server actions for authentication.
 */

"use server";

import { createServerSupabase } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

/**
 * Signs the user out and redirects to the login page.
 */
export async function logoutAction() {
  const supabase = await createServerSupabase();
  await supabase.auth.signOut();
  redirect("/login");
}
