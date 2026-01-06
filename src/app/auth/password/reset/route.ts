/**
 * @fileoverview Password reset route handler using Supabase SSR.
 */

import "server-only";

import { passwordResetPayloadSchema } from "@schemas/auth";
import type { EmailOtpType } from "@supabase/supabase-js";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { parseJsonBody } from "@/lib/api/route-helpers";
import { createServerSupabase } from "@/lib/supabase/server";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { createServerLogger } from "@/lib/telemetry/logger";

const MAX_BODY_BYTES = 16 * 1024;
const OTP_TYPE: EmailOtpType = "recovery";
const logger = createServerLogger("auth.password.reset");

export async function POST(request: NextRequest): Promise<NextResponse> {
  const parsedBody = await parseJsonBody(request, { maxBytes: MAX_BODY_BYTES });
  if (!parsedBody.ok) {
    if (parsedBody.error.status === 413) {
      return NextResponse.json(
        { code: "PAYLOAD_TOO_LARGE", message: "Request body exceeds limit" },
        { status: 413 }
      );
    }
    return NextResponse.json(
      { code: "BAD_REQUEST", message: "Malformed JSON" },
      { status: 400 }
    );
  }

  const payload = passwordResetPayloadSchema.safeParse(parsedBody.data);
  if (!payload.success) {
    // Sanitize validation errors for auth endpoints - expose only field names, not internal codes
    const fieldErrors = payload.error.issues.map(({ message, path }) => ({
      field: path.length > 0 ? String(path[0]) : "unknown",
      message,
    }));
    return NextResponse.json(
      {
        code: "VALIDATION_ERROR",
        errors: fieldErrors,
        message: "Invalid password reset payload",
      },
      { status: 400 }
    );
  }

  const { token, newPassword } = payload.data;

  const supabase = await createServerSupabase();

  // Verify the password recovery token.
  const { error: verifyError } = await supabase.auth.verifyOtp({
    token_hash: token,
    type: OTP_TYPE,
  });

  if (verifyError) {
    emitOperationalAlertOncePerWindow({
      attributes: {
        errorCode: verifyError.code ?? null,
        reason: "verify_otp_failed",
        status: verifyError.status ?? null,
      },
      event: "auth.password.reset.verify_failed",
      severity: "warning",
      windowMs: 60_000,
    });
    logger.warn("password reset token verification failed", {
      errorCode: verifyError.code,
      status: verifyError.status,
    });
    // Use uniform error code to avoid leaking which step failed
    return NextResponse.json(
      { code: "RESET_FAILED", message: "Password reset failed" },
      { status: 400 }
    );
  }

  const { error: updateError } = await supabase.auth.updateUser({
    password: newPassword,
  });

  if (updateError) {
    emitOperationalAlertOncePerWindow({
      attributes: {
        errorCode: updateError.code ?? null,
        reason: "update_failed",
        status: updateError.status ?? null,
      },
      event: "auth.password.reset.update_failed",
      severity: "warning",
      windowMs: 60_000,
    });
    logger.error("password reset update failed", {
      errorCode: updateError.code,
      status: updateError.status,
    });
    // Use uniform error code to avoid leaking which step failed
    return NextResponse.json(
      { code: "RESET_FAILED", message: "Password reset failed" },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
