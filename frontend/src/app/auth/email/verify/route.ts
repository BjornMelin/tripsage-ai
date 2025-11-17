/**
 * @fileoverview Email verification route handler using Supabase SSR.
 *
 * Accepts a token payload and verifies the user's email via Supabase Auth.
 * This is primarily intended for programmatic verification flows driven by
 * the AuthValidation store.
 */

import "server-only";

import type { EmailOtpType } from "@supabase/supabase-js";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

interface VerifyPayload {
  token?: unknown;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let payload: VerifyPayload;
  try {
    payload = (await request.json()) as VerifyPayload;
  } catch {
    return NextResponse.json(
      { code: "BAD_REQUEST", message: "Malformed JSON" },
      { status: 400 }
    );
  }

  const token = typeof payload.token === "string" ? payload.token : "";
  if (!token) {
    return NextResponse.json(
      { code: "VALIDATION_ERROR", message: "Verification token is required" },
      { status: 400 }
    );
  }

  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.verifyOtp({
    token_hash: token,
    type: "email" as EmailOtpType,
  });

  if (error) {
    return NextResponse.json(
      { code: "VERIFICATION_FAILED", message: error.message },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
