import { mfaVerificationInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { regenerateBackupCodes, verifyTotp } from "@/lib/security/mfa";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

export const dynamic = "force-dynamic";
const logger = createServerLogger("api.auth.mfa.verify", {
  redactKeys: ["challengeId", "factorId", "code"],
});

export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:verify",
  schema: mfaVerificationInputSchema,
  telemetry: "api.auth.mfa.verify",
})(async (_req, { supabase, user }, data) => {
  try {
    await verifyTotp(supabase, data);
  } catch (error) {
    logger.error("totp verification failed", {
      error: error instanceof Error ? error.message : "unknown_error",
    });
    return NextResponse.json({ error: "invalid_or_expired_code" }, { status: 400 });
  }

  const userId = user?.id ?? (await supabase.auth.getUser()).data.user?.id;
  let backupCodes: string[] | undefined;
  if (userId) {
    try {
      const admin = createAdminSupabase();
      const regenerated = await regenerateBackupCodes(admin, userId, 10);
      backupCodes = regenerated.codes;
    } catch (error) {
      logger.error("failed to regenerate backup codes post-verify", {
        error: error instanceof Error ? error.message : "unknown_error",
      });
    }
  }

  return NextResponse.json({ data: { backupCodes, status: "verified" } });
});
