/**
 * @fileoverview API route for verifying MFA backup codes.
 */

import { backupCodeVerifyInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getClientIpFromHeaders } from "@/lib/api/route-helpers";
import {
  InvalidBackupCodeError,
  requireAal2,
  verifyBackupCode,
} from "@/lib/security/mfa";
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
})(async (req, { user, supabase }, data) => {
  if (!user) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  try {
    // Enforce strong auth level before backup code consumption
    await requireAal2(supabase);
    const admin = getAdminSupabase();
    const ip = getClientIpFromHeaders(req);
    const userAgent = req.headers.get("user-agent") ?? undefined;
    const result = await verifyBackupCode(admin, user.id, data.code, {
      ip,
      userAgent,
    });
    return NextResponse.json({ data: { remaining: result.remaining, success: true } });
  } catch (error) {
    const invalid = error instanceof InvalidBackupCodeError;
    logger.error("backup code verification failed", {
      ip: getClientIpFromHeaders(req),
      reason: invalid ? error.message : "internal_error",
      timestamp: nowIso(),
      userId: user.id,
    });

    if (invalid) {
      return NextResponse.json(
        { data: { remaining: 0, success: false } },
        { status: 400 }
      );
    }

    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
});
