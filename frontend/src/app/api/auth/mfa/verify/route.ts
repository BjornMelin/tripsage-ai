/**
 * @fileoverview The API route for verifying a MFA code.
 */

import "server-only";

import { mfaVerificationInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  getClientIpFromHeaders,
  unauthorizedResponse,
} from "@/lib/api/route-helpers";
import {
  InvalidTotpError,
  regenerateBackupCodes,
  TotpVerificationInternalError,
  verifyTotp,
} from "@/lib/security/mfa";
import { getAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for the MFA verify API. */
export const dynamic = "force-dynamic";

const logger = createServerLogger("api.auth.mfa.verify", {
  redactKeys: ["challengeId", "factorId", "code"],
});

/** The POST handler for the MFA verify API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:verify",
  schema: mfaVerificationInputSchema,
  telemetry: "api.auth.mfa.verify",
})(async (req, { supabase, user }, data) => {
  const adminSupabase = getAdminSupabase();
  let isInitialEnrollment = false;
  try {
    const result = await verifyTotp(supabase, data, { adminSupabase });
    isInitialEnrollment = result.isInitialEnrollment;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error ?? "");
    const status = (error as { status?: number } | null)?.status;
    const isInternalError =
      typeof TotpVerificationInternalError === "function" &&
      error instanceof TotpVerificationInternalError;
    const shouldReturnServerError =
      isInternalError || (typeof status === "number" && status >= 500);
    if (!shouldReturnServerError) {
      const errorCode =
        error instanceof InvalidTotpError
          ? error.code
          : ((error as { code?: string } | null)?.code ?? "invalid_or_expired_code");
      return errorResponse({
        error: errorCode,
        reason: "Invalid or expired MFA code",
        status: 400,
      });
    }
    logger.error("totp verification failed", {
      error: message || "unknown_error",
      errorType:
        error instanceof TotpVerificationInternalError
          ? error.name
          : error?.constructor?.name,
      factorId: data.factorId,
    });
    return errorResponse({
      err: error,
      error: "mfa_verification_failed",
      reason: "TOTP verification failed",
      status: 500,
    });
  }

  // Only generate backup codes during initial MFA enrollment, not on subsequent logins
  // Additional safeguard: verify user doesn't already have backup codes (prevents regeneration on regular challenges)
  let backupCodes: string[] | undefined;
  if (isInitialEnrollment) {
    if (!user?.id) {
      return unauthorizedResponse();
    }
    const userId = user.id;

    // Defensive check: only generate backup codes if user doesn't already have any
    // This prevents regeneration during regular MFA challenges where isInitialEnrollment might be incorrectly true
    const { count: backupCodesCount, error: backupCodesQueryError } =
      await adminSupabase
        .from("auth_backup_codes")
        .select("id", { count: "exact", head: true })
        .eq("user_id", userId)
        .is("consumed_at", null);

    if (backupCodesQueryError) {
      return errorResponse({
        err: backupCodesQueryError,
        error: "failed_to_fetch_backup_codes",
        reason: "Failed to check existing backup codes",
        status: 500,
      });
    }

    const existingBackupCodesCount =
      typeof backupCodesCount === "number" ? backupCodesCount : 0;

    if (existingBackupCodesCount === 0) {
      const ip = getClientIpFromHeaders(req);
      const userAgent = req.headers.get("user-agent") ?? undefined;
      try {
        const regenerated = await regenerateBackupCodes(adminSupabase, userId, 10, {
          ip,
          userAgent,
        });
        backupCodes = regenerated.codes;
      } catch (error) {
        logger.error("failed to generate backup codes post-enrollment", {
          error: error instanceof Error ? error.message : "unknown_error",
          userId,
        });
      }
    } else {
      logger.warn("skipped backup code generation: user already has backup codes", {
        existingCount: existingBackupCodesCount,
        userId,
      });
    }
  }

  return NextResponse.json({ data: { backupCodes, status: "verified" } });
});
