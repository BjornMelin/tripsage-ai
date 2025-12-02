import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { startTotpEnrollment } from "@/lib/security/mfa";
import { createServerLogger } from "@/lib/telemetry/logger";

export const dynamic = "force-dynamic";
const logger = createServerLogger("api.auth.mfa.setup");

export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:setup",
  telemetry: "api.auth.mfa.setup",
})(async (_req, { supabase }) => {
  try {
    const enrollment = await startTotpEnrollment(supabase);
    return NextResponse.json({
      data: {
        challengeId: enrollment.challengeId,
        expiresAt: enrollment.expiresAt,
        factorId: enrollment.factorId,
        issuedAt: enrollment.issuedAt,
        qrCode: enrollment.qrCode,
        ttlSeconds: enrollment.ttlSeconds,
        uri: enrollment.uri,
      },
    });
  } catch (error) {
    logger.error("mfa setup failed", {
      error: error instanceof Error ? error.message : "unknown_error",
    });
    return NextResponse.json({ error: "mfa_setup_failed" }, { status: 500 });
  }
});
