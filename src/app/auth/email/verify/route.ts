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
import { parseJsonBody } from "@/lib/api/route-helpers";
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
  if ("error" in parsed) {
    if (parsed.error.status === 413) {
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

  const payload: VerifyPayload = isPlainObject(parsed.body) ? parsed.body : {};

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
    return NextResponse.json(
      { code: "VERIFICATION_FAILED", message: "Verification failed" },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true });
}
