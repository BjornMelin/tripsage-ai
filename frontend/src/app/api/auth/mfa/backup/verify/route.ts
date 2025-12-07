/**
 * @fileoverview API route for verifying MFA backup codes.
 */

import "server-only";

import { backupCodeVerifyInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getClientIpFromHeaders } from "@/lib/api/route-helpers";
import { InvalidBackupCodeError, verifyBackupCode } from "@/lib/security/mfa";
import { nowIso } from "@/lib/security/random";
import { getAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for the MFA backup code verify API. */
export const dynamic = "force-dynamic";

/** The logger for the MFA backup code verify API. */
const logger = createServerLogger("api.auth.mfa.backup.verify", {
  redactKeys: ["code"],
});

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
      return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
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
    logger.error("backup code verification failed", {
      ip,
      reason: invalid ? error.message : "internal_error",
      timestamp: nowIso(),
      userId: user?.id,
    });

    if (invalid) {
      return NextResponse.json({ error: "invalid_backup_code" }, { status: 400 });
    }

    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
});
