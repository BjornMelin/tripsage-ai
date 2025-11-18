/**
 * @fileoverview Password reset request route handler.
 *
 * Sends Supabase password reset emails using SSR Supabase client. This route is
 * public and does not require authentication.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { resetPasswordFormSchema } from "@/lib/schemas/forms";
import { createServerSupabase } from "@/lib/supabase/server";

interface ResetRequestPayload {
  email?: unknown;
}

/**
 * Handles POST /auth/password/reset-request.
 *
 * Validates the email address and calls Supabase Auth
 * resetPasswordForEmail with a redirect URL pointing back to the app.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  let payload: ResetRequestPayload;
  try {
    payload = (await request.json()) as ResetRequestPayload;
  } catch {
    return NextResponse.json(
      { code: "BAD_REQUEST", error: "Malformed JSON" },
      { status: 400 }
    );
  }

  const parsed = resetPasswordFormSchema.safeParse({
    email: payload.email,
  });

  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    const message = issue?.message ?? "Email is required";
    return NextResponse.json(
      { code: "VALIDATION_ERROR", error: message },
      { status: 400 }
    );
  }

  const { email } = parsed.data;

  const supabase = await createServerSupabase();
  const origin = new URL(request.url).origin;
  const emailRedirectTo = `${origin}/auth/reset-password`;

  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: emailRedirectTo,
  });

  if (error) {
    return NextResponse.json(
      { code: "RESET_REQUEST_FAILED", error: error.message },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
