import { backupCodeVerifyInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { verifyBackupCode } from "@/lib/security/mfa";
import { createAdminSupabase } from "@/lib/supabase/admin";

export const dynamic = "force-dynamic";

export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:backup:verify",
  schema: backupCodeVerifyInputSchema,
  telemetry: "api.auth.mfa.backup.verify",
})(async (_req, { user }, data) => {
  if (!user) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  try {
    const admin = createAdminSupabase();
    const result = await verifyBackupCode(admin, user.id, data.code);
    return NextResponse.json({ data: { remaining: result.remaining, success: true } });
  } catch {
    return NextResponse.json(
      { data: { remaining: 0, success: false } },
      { status: 400 }
    );
  }
});
