/**
 * @fileoverview Supabase email confirmation route.
 * Exchanges a token_hash for a session using Supabase SSR and redirects.
 * Reference: Supabase SSR Next.js guide (Auth confirmation).
 */

import "server-only";

import type { EmailOtpType } from "@supabase/supabase-js";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { sanitizeAuthConfirmNextParam } from "@/lib/auth/confirm-next";
import { createServerSupabase } from "@/lib/supabase/server";

const ALLOWED_EMAIL_OTP_TYPES = new Set<string>([
  "email",
  "email_change",
  "invite",
  "magiclink",
  "recovery",
  "signup",
]);

function parseEmailOtpType(value: string | null): EmailOtpType | null {
  if (!value) return null;
  return ALLOWED_EMAIL_OTP_TYPES.has(value) ? (value as EmailOtpType) : null;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const tokenHash = searchParams.get("token_hash");
  const type = parseEmailOtpType(searchParams.get("type"));
  const next = sanitizeAuthConfirmNextParam(searchParams.get("next"));

  if (tokenHash && type) {
    const supabase = await createServerSupabase();
    const { error } = await supabase.auth.verifyOtp({
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
