/**
 * @fileoverview Email verification route handler using Supabase SSR.
 */

import "server-only";

import type { EmailOtpType } from "@supabase/supabase-js";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { parseJsonBody } from "@/lib/api/route-helpers";
import { authRouteErrorResponse } from "@/lib/auth/route-error-response";
import { createServerSupabase } from "@/lib/supabase/server";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { createServerLogger } from "@/lib/telemetry/logger";
import { isPlainObject } from "@/lib/utils/type-guards";

interface VerifyPayload {
  token?: unknown;
}

const MAX_BODY_BYTES = 16 * 1024;
const logger = createServerLogger("auth.email.verify");

export async function POST(request: NextRequest): Promise<NextResponse> {
  const parsed = await parseJsonBody(request, { maxBytes: MAX_BODY_BYTES });
  if (!parsed.ok) {
    if (parsed.error.status === 413) {
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

  const payload: VerifyPayload = isPlainObject(parsed.data) ? parsed.data : {};

  const token = typeof payload.token === "string" ? payload.token : "";
  if (!token) {
    return authRouteErrorResponse({
      code: "VALIDATION_ERROR",
      reason: "Verification token is required",
      status: 400,
    });
  }

  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.verifyOtp({
    token_hash: token,
    type: "email" as EmailOtpType,
  });

  if (error) {
    emitOperationalAlertOncePerWindow({
      attributes: {
        errorCode: error.code ?? null,
        reason: "verify_otp_failed",
        status: error.status ?? null,
      },
      event: "auth.email.verify.failed",
      severity: "warning",
      windowMs: 60_000,
    });
    logger.warn("email verification failed", {
      errorCode: error.code,
      status: error.status,
    });
    return authRouteErrorResponse({
      code: "VERIFICATION_FAILED",
      reason: "Verification failed",
      status: 400,
    });
  }

  return NextResponse.json({ ok: true });
}
