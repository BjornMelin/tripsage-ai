/**
 * @fileoverview Authenticated password change route handler.
 *
 * Allows a logged-in user to change their password using the Supabase SSR
 * client. Validates input and returns JSON responses suitable for the
 * AuthValidation store.
 */

import "server-only";

import { changePasswordFormSchema } from "@schemas/auth";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth/server";

interface ChangePasswordPayload {
  confirmPassword?: unknown;
  currentPassword?: unknown;
  newPassword?: unknown;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let payload: ChangePasswordPayload;
  try {
    payload = (await request.json()) as ChangePasswordPayload;
  } catch {
    return NextResponse.json(
      { code: "BAD_REQUEST", message: "Malformed JSON" },
      { status: 400 }
    );
  }

  const parsed = changePasswordFormSchema.safeParse({
    confirmPassword: payload.confirmPassword,
    currentPassword: payload.currentPassword,
    newPassword: payload.newPassword,
  });

  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    return NextResponse.json(
      { code: "VALIDATION_ERROR", message: issue?.message ?? "Invalid input" },
      { status: 400 }
    );
  }

  const { supabase, user } = await requireUser({ redirectTo: "/settings/security" });
  const email = user.email;

  if (!email) {
    return NextResponse.json(
      { code: "EMAIL_REQUIRED", message: "User email is required to change password" },
      { status: 400 }
    );
  }

  // Verify current password by attempting a sign-in with the provided credentials.
  const { error: signInError } = await supabase.auth.signInWithPassword({
    email,
    password: parsed.data.currentPassword,
  });

  if (signInError) {
    return NextResponse.json(
      { code: "INVALID_CREDENTIALS", message: "Current password is incorrect" },
      { status: 400 }
    );
  }

  const { error: updateError } = await supabase.auth.updateUser({
    password: parsed.data.newPassword,
  });

  if (updateError) {
    return NextResponse.json(
      { code: "UPDATE_FAILED", message: updateError.message },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
