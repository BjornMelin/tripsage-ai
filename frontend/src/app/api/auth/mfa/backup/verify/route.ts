/**
 * @fileoverview API route for verifying MFA backup codes.
 */

import "server-only";

import { backupCodeVerifyInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  getClientIpFromHeaders,
  unauthorizedResponse,
} from "@/lib/api/route-helpers";
import { InvalidBackupCodeError, verifyBackupCode } from "@/lib/security/mfa";
import { getAdminSupabase } from "@/lib/supabase/admin";

/** The dynamic route for the MFA backup code verify API. */
export const dynamic = "force-dynamic";

/** The POST handler for the MFA backup code verify API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:backup:verify",
  schema: backupCodeVerifyInputSchema,
  telemetry: "api.auth.mfa.backup.verify",
})(async (req, { user }, data) => {
  const ip = getClientIpFromHeaders(req);
  try {
    const admin = getAdminSupabase();
    const userAgent = req.headers.get("user-agent") ?? undefined;
    if (!user?.id) {
      return unauthorizedResponse();
    }
    // Note: No requireAal2() check here - backup codes must be usable at AAL1
    // when the primary MFA factor is unavailable (account recovery scenario)
    const result = await verifyBackupCode(admin, user.id, data.code, {
      ip,
      userAgent,
    });
    return NextResponse.json({
      data: { remaining: result.remaining, success: true },
    });
  } catch (error) {
    const invalid = error instanceof InvalidBackupCodeError;

    if (invalid) {
      return errorResponse({
        err: error,
        error: "invalid_backup_code",
        reason: "Backup code is invalid or already used",
        status: 400,
      });
    }

    return errorResponse({
      err: error,
      error: "internal_error",
      reason: "Backup code verification failed",
      status: 500,
    });
  }
});
