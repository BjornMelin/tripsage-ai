/**
 * @fileoverview Email verification resend route handler.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { authRouteErrorResponse } from "@/lib/auth/route-error-response";
import { requireUser } from "@/lib/auth/server";
import { ROUTES } from "@/lib/routes";

export async function POST(_request: NextRequest): Promise<NextResponse> {
  const { supabase, user } = await requireUser({
    redirectTo: ROUTES.dashboard.settings,
  });

  if (!user.email) {
    return authRouteErrorResponse({
      code: "EMAIL_REQUIRED",
      reason: "User email is required to resend verification",
      status: 400,
    });
  }

  const { error } = await supabase.auth.resend({
    email: user.email,
    type: "signup",
  });

  if (error) {
    return authRouteErrorResponse({
      code: "RESEND_FAILED",
      reason: error.message,
      status: 400,
    });
  }

  return NextResponse.json({ ok: true });
}
