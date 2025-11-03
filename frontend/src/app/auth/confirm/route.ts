/**
 * @fileoverview Supabase email confirmation route.
 * Exchanges a token_hash for a session using Supabase SSR and redirects.
 * Reference: Supabase SSR Next.js guide (Auth confirmation).
 */

import type { EmailOtpType } from "@supabase/supabase-js";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/";

  if (tokenHash && type) {
    const supabase = await createServerSupabase();
    const { error } = await supabase.auth.verifyOtp({
      // biome-ignore lint/style/useNamingConvention: Supabase API parameter
      token_hash: tokenHash,
      type,
    });
    if (!error) {
      redirect(next);
    }
  }

  // On error, redirect to a friendly error page or home
  redirect("/error");
}
