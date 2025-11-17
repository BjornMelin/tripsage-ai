/**
 * @fileoverview Email verification resend route handler.
 *
 * Authenticated route that triggers Supabase Auth to resend a signup
 * verification email to the current user's email address.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth/server";

export async function POST(_request: NextRequest): Promise<NextResponse> {
  const { supabase, user } = await requireUser({ redirectTo: "/settings" });

  if (!user.email) {
    return NextResponse.json(
      {
        code: "EMAIL_REQUIRED",
        message: "User email is required to resend verification",
      },
      { status: 400 }
    );
  }

  const { error } = await supabase.auth.resend({
    email: user.email,
    type: "signup",
  });

  if (error) {
    return NextResponse.json(
      { code: "RESEND_FAILED", message: error.message },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
