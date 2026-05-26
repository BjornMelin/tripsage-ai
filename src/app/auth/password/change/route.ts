/**
 * @fileoverview Authenticated password change route handler.
 */

import "server-only";

import { changePasswordPayloadSchema } from "@schemas/auth";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { type RouteContext, withApiGuards } from "@/lib/api/factory";
import { parseJsonBody } from "@/lib/api/route-helpers";
import { authRouteErrorResponse } from "@/lib/auth/route-error-response";
import {
  getAuthErrorCode,
  getAuthErrorStatus,
  isMfaRequiredError,
} from "@/lib/auth/supabase-errors";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { createServerLogger } from "@/lib/telemetry/logger";
import { isPlainObject } from "@/lib/utils/type-guards";

interface ChangePasswordPayload {
  currentPassword?: unknown;
  newPassword?: unknown;
}

// Password change payloads are tiny; keep a tight limit to reduce DoS surface.
const MAX_BODY_BYTES = 4 * 1024;

const logger = createServerLogger("auth.password.change");

async function handlePasswordChange(
  request: NextRequest,
  { supabase, user }: RouteContext
): Promise<NextResponse> {
  const parsedBody = await parseJsonBody(request, { maxBytes: MAX_BODY_BYTES });
  if (!parsedBody.ok) {
    if (parsedBody.error.status === 413) {
      return authRouteErrorResponse({
        code: "PAYLOAD_TOO_LARGE",
        reason: "Request body exceeds limit",
        status: 413,
      });
    }
    return authRouteErrorResponse({
      code: "BAD_REQUEST",
      reason: "Malformed JSON",
      status: 400,
    });
  }

  const payload: ChangePasswordPayload = isPlainObject(parsedBody.data)
    ? parsedBody.data
    : {};

  const parsed = changePasswordPayloadSchema.safeParse({
    currentPassword: payload.currentPassword,
    newPassword: payload.newPassword,
  });

  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    return authRouteErrorResponse({
      code: "VALIDATION_ERROR",
      reason: issue?.message ?? "Invalid input",
      status: 400,
    });
  }

  const email = user?.email;

  if (!email) {
    return authRouteErrorResponse({
      code: "EMAIL_REQUIRED",
      reason: "User email is required to change password",
      status: 400,
    });
  }

  // Verify current password by attempting a sign-in with the provided credentials.
  const { error: signInError } = await supabase.auth.signInWithPassword({
    email,
    password: parsed.data.currentPassword,
  });

  if (isMfaRequiredError(signInError)) {
    return authRouteErrorResponse({
      code: signInError.code ?? "mfa_required",
      reason: "Multi-factor authentication required",
      status: 403,
    });
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
      return authRouteErrorResponse({
        code: "AUTH_UPSTREAM_ERROR",
        reason: "Password verification temporarily unavailable",
        status: 503,
      });
    }

    return authRouteErrorResponse({
      code: "INVALID_CREDENTIALS",
      reason: "Current password is incorrect",
      status: 400,
    });
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
      return authRouteErrorResponse({
        code: "AUTH_UPSTREAM_ERROR",
        reason: "Password update temporarily unavailable",
        status: 503,
      });
    }

    return authRouteErrorResponse({
      code: "UPDATE_FAILED",
      reason: "Password update failed",
      status: 400,
    });
  }

  return NextResponse.json({ ok: true });
}

/**
 * Changes the authenticated user's password through the guarded route pipeline.
 *
 * @param req - Next.js request containing the current and new password.
 * @returns JSON response describing the password change result.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:password:change",
  telemetry: "auth.password.change",
})(handlePasswordChange);
