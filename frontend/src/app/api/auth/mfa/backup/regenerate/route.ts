/**
 * @fileoverview API route for regenerating MFA backup codes.
 */

import "server-only";

import { backupCodeRegenerateInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  forbiddenResponse,
  getClientIpFromHeaders,
  unauthorizedResponse,
} from "@/lib/api/route-helpers";
import {
  MfaRequiredError,
  regenerateBackupCodes,
  requireAal2,
} from "@/lib/security/mfa";
import { getAdminSupabase } from "@/lib/supabase/admin";

/** The dynamic route for the MFA backup code regenerate API. */
export const dynamic = "force-dynamic";

/** The POST handler for the MFA backup code regenerate API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:backup:regenerate",
  schema: backupCodeRegenerateInputSchema,
  telemetry: "api.auth.mfa.backup.regenerate",
})(async (req, { user, supabase }, data) => {
  try {
    if (!user?.id) {
      return unauthorizedResponse();
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
      return forbiddenResponse("MFA verification required to regenerate backup codes");
    }
    return errorResponse({
      err: error,
      error: "backup_regenerate_failed",
      reason: "Failed to regenerate backup codes",
      status: 500,
    });
  }
});
