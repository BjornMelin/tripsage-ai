/**
 * @fileoverview Supabase email confirmation route. Exchanges a token_hash for a session using Supabase SSR and redirects. Reference: Supabase SSR Next.js guide (Auth confirmation).
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
  const next = sanitizeAuthConfirmNextParam(searchParams.get("next"));

  // Supabase may redirect here with an error payload (e.g., expired link) without token_hash/type.
  // Route to a user-facing page instead of a non-existent /error path.
  const error = searchParams.get("error");
  const errorCode = searchParams.get("error_code");
  if (error || errorCode) {
    const params = new URLSearchParams({ error: "auth_confirm_failed", next });
    if (errorCode) params.set("error_code", errorCode);
    redirect(`/login?${params.toString()}`);
  }

  // Supabase OAuth + PKCE flows redirect with `code` to be exchanged for a session.
  const code = searchParams.get("code");
  if (code) {
    const supabase = await createServerSupabase();
    const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
    if (!exchangeError) {
      redirect(next);
    }
  }

  const tokenHash = searchParams.get("token_hash");
  const type = parseEmailOtpType(searchParams.get("type"));

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

  const fallback = new URLSearchParams({ error: "auth_confirm_failed", next });
  redirect(`/login?${fallback.toString()}`);
}
