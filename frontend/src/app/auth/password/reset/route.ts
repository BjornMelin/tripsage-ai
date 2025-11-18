/**
 * @fileoverview Password reset route handler using Supabase SSR.
 *
 * Accepts a password reset token and new password, verifies the token using
 * Supabase Auth, and then updates the user's password.
 */

import "server-only";

import type { EmailOtpType } from "@supabase/supabase-js";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

interface ResetPayload {
  newPassword?: unknown;
  token?: unknown;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let payload: ResetPayload;
  try {
    payload = (await request.json()) as ResetPayload;
  } catch {
    return NextResponse.json(
      { code: "BAD_REQUEST", message: "Malformed JSON" },
      { status: 400 }
    );
  }

  const token = typeof payload.token === "string" ? payload.token : "";
  const newPassword =
    typeof payload.newPassword === "string" ? payload.newPassword : "";

  if (!token || !newPassword) {
    return NextResponse.json(
      { code: "VALIDATION_ERROR", message: "Token and new password are required" },
      { status: 400 }
    );
  }

  const supabase = await createServerSupabase();

  // Verify the password recovery token.
  const { error: verifyError } = await supabase.auth.verifyOtp({
    token_hash: token,
    type: "recovery" as EmailOtpType,
  });

  if (verifyError) {
    return NextResponse.json(
      { code: "INVALID_TOKEN", message: verifyError.message },
      { status: 400 }
    );
  }

  const { error: updateError } = await supabase.auth.updateUser({
    password: newPassword,
  });

  if (updateError) {
    return NextResponse.json(
      { code: "UPDATE_FAILED", message: updateError.message },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
