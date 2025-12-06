/**
 * @fileoverview API route for regenerating MFA backup codes.
 */

import { backupCodeRegenerateInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getClientIpFromHeaders } from "@/lib/api/route-helpers";
import {
  MfaRequiredError,
  regenerateBackupCodes,
  requireAal2,
} from "@/lib/security/mfa";
import { getAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for the MFA backup code regenerate API. */
export const dynamic = "force-dynamic";

/** The logger for the MFA backup code regenerate API. */
const logger = createServerLogger("api.auth.mfa.backup.regenerate");

/** The POST handler for the MFA backup code regenerate API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:backup:regenerate",
  schema: backupCodeRegenerateInputSchema,
  telemetry: "api.auth.mfa.backup.regenerate",
})(async (req, { user, supabase }, data) => {
  try {
    if (!user?.id) {
      return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
    }
    await requireAal2(supabase);
    const ip = getClientIpFromHeaders(req);
    const userAgent = req.headers.get("user-agent") ?? undefined;
    const admin = getAdminSupabase();
    const result = await regenerateBackupCodes(admin, user.id, data.count, {
      ip,
      userAgent,
    });
    return NextResponse.json({ data: { backupCodes: result.codes } });
  } catch (error) {
    if (
      error instanceof MfaRequiredError ||
      (error as { code?: string } | null)?.code === "MFA_REQUIRED"
    ) {
      return NextResponse.json({ error: "mfa_required" }, { status: 403 });
    }
    logger.error("backup code regeneration failed", {
      count: data.count,
      error: error instanceof Error ? error.message : "unknown_error",
      userId: user?.id,
    });
    return NextResponse.json({ error: "backup_regenerate_failed" }, { status: 500 });
  }
});
