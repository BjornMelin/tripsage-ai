import { backupCodeRegenerateInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { regenerateBackupCodes } from "@/lib/security/mfa";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

export const dynamic = "force-dynamic";
const logger = createServerLogger("api.auth.mfa.backup.regenerate");

export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:backup:regenerate",
  schema: backupCodeRegenerateInputSchema,
  telemetry: "api.auth.mfa.backup.regenerate",
})(async (_req, { user }, data) => {
  try {
    if (!user?.id) {
      throw new Error("user_missing");
    }
    const admin = createAdminSupabase();
    const result = await regenerateBackupCodes(admin, user.id, data.count);
    return NextResponse.json({ data: { backupCodes: result.codes } });
  } catch (error) {
    logger.error("backup code regeneration failed", {
      count: data.count,
      error: error instanceof Error ? error.message : "unknown_error",
      userId: user?.id,
    });
    return NextResponse.json({ error: "backup_regenerate_failed" }, { status: 500 });
  }
});
