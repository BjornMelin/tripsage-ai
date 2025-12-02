/**
 * @fileoverview The API route for verifying a MFA code.
 */

import { mfaVerificationInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { regenerateBackupCodes, verifyTotp } from "@/lib/security/mfa";
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
})(async (_req, { supabase, user }, data) => {
  const adminSupabase = getAdminSupabase();
  let isInitialEnrollment = false;
  try {
    const result = await verifyTotp(supabase, data, { adminSupabase });
    isInitialEnrollment = result.isInitialEnrollment;
  } catch (error) {
    logger.error("totp verification failed", {
      error: error instanceof Error ? error.message : "unknown_error",
    });
    return NextResponse.json({ error: "invalid_or_expired_code" }, { status: 400 });
  }

  // Only generate backup codes during initial MFA enrollment, not on subsequent logins
  let backupCodes: string[] | undefined;
  if (isInitialEnrollment) {
    const userId = user?.id ?? (await supabase.auth.getUser()).data.user?.id;
    if (userId) {
      try {
        const regenerated = await regenerateBackupCodes(adminSupabase, userId, 10);
        backupCodes = regenerated.codes;
      } catch (error) {
        logger.error("failed to generate backup codes post-enrollment", {
          error: error instanceof Error ? error.message : "unknown_error",
        });
      }
    }
  }

  return NextResponse.json({ data: { backupCodes, status: "verified" } });
});
