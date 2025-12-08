/**
 * @fileoverview Login API route.
 *
 * Handles email/password login authentication using Supabase SSR.
 * Uses withApiGuards for rate limiting, validation, and telemetry.
 */

import "server-only";

import { loginFormSchema } from "@schemas/auth";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";

/**
 * POST /api/auth/login
 *
 * Authenticates a user with email and password.
 * Returns success/error status without redirects (client handles navigation).
 *
 * Rate limited to 5 requests/minute per IP.
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "auth:login",
  schema: loginFormSchema,
  telemetry: "auth.login",
})(async (_req, { supabase }, data) => {
  const { error } = await supabase.auth.signInWithPassword({
    email: data.email,
    password: data.password,
  });

  if (isMfaRequiredError(error)) {
    return NextResponse.json(
      {
        code: error.code,
        error: "mfa_required",
        reason: "Multi-factor authentication required",
      },
      { status: 403 }
    );
  }

  if (error) {
    return errorResponse({
      err: error,
      error: "invalid_credentials",
      reason: "Invalid email or password",
      status: 401,
    });
  }

  return NextResponse.json({ success: true });
});

function isMfaRequiredError(
  err: unknown
): err is { code?: string; message?: string; status?: number } {
  if (!err || typeof err !== "object") {
    return false;
  }

  const { code, message, status } = err as {
    code?: string;
    message?: string;
    status?: number;
  };

  if (code === "insufficient_aal" || code === "mfa_required") {
    return true;
  }

  if (status === 403) {
    const normalized = message?.toLowerCase() ?? "";
    return normalized.includes("mfa") || normalized.includes("aal");
  }

  return false;
}
