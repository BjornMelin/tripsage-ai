/**
 * @fileoverview Authenticated password change route handler.
 */

import "server-only";

import { changePasswordFormSchema } from "@schemas/auth";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { parseJsonBody } from "@/lib/api/route-helpers";
import { requireUser } from "@/lib/auth/server";
import {
  getAuthErrorCode,
  getAuthErrorStatus,
  isMfaRequiredError,
} from "@/lib/auth/supabase-errors";
import { ROUTES } from "@/lib/routes";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { createServerLogger } from "@/lib/telemetry/logger";
import { isPlainObject } from "@/lib/utils/type-guards";

interface ChangePasswordPayload {
  confirmPassword?: unknown;
  currentPassword?: unknown;
  newPassword?: unknown;
}

// Password change payloads are tiny; keep a tight limit to reduce DoS surface.
const MAX_BODY_BYTES = 4 * 1024;

const logger = createServerLogger("auth.password.change");

export async function POST(request: NextRequest): Promise<NextResponse> {
  const parsedBody = await parseJsonBody(request, { maxBytes: MAX_BODY_BYTES });
  if ("error" in parsedBody) {
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

  const payload: ChangePasswordPayload = isPlainObject(parsedBody.body)
    ? parsedBody.body
    : {};

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

  const { supabase, user } = await requireUser({
    redirectTo: ROUTES.dashboard.security,
  });
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

  if (isMfaRequiredError(signInError)) {
    return NextResponse.json(
      {
        code: signInError.code ?? "mfa_required",
        message: "Multi-factor authentication required",
      },
      { status: 403 }
    );
  }

  if (signInError) {
    const status = getAuthErrorStatus(signInError) ?? 500;
    const errorCode = getAuthErrorCode(signInError);

    if (status === 429 || status >= 500) {
      emitOperationalAlertOncePerWindow({
        attributes: {
          errorCode,
          reason: "supabase_error",
          status,
        },
        event: "auth.password.change.upstream_error",
        severity: "warning",
        windowMs: 60_000,
      });
      logger.error("password change auth verification failed", {
        errorCode,
        status,
      });
      return NextResponse.json(
        {
          code: "AUTH_UPSTREAM_ERROR",
          message: "Password verification temporarily unavailable",
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { code: "INVALID_CREDENTIALS", message: "Current password is incorrect" },
      { status: 400 }
    );
  }

  const { error: updateError } = await supabase.auth.updateUser({
    password: parsed.data.newPassword,
  });

  if (updateError) {
    const upstreamStatus = getAuthErrorStatus(updateError) ?? 500;
    const errorCode = getAuthErrorCode(updateError);

    emitOperationalAlertOncePerWindow({
      attributes: {
        errorCode: errorCode ?? null,
        reason: "update_failed",
        status: upstreamStatus,
      },
      event: "auth.password.change.update_failed",
      severity: "warning",
      windowMs: 60_000,
    });
    logger.error("password change update failed", {
      errorCode,
      status: upstreamStatus,
    });

    // Distinguish upstream service errors from validation failures
    if (upstreamStatus >= 500 || upstreamStatus === 429) {
      return NextResponse.json(
        {
          code: "AUTH_UPSTREAM_ERROR",
          message: "Password update temporarily unavailable",
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { code: "UPDATE_FAILED", message: "Password update failed" },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
