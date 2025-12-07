/**
 * @fileoverview The API route for setting up MFA.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { startTotpEnrollment } from "@/lib/security/mfa";
import { getAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for setting up MFA. */
export const dynamic = "force-dynamic";

/** The logger for the MFA setup API. */
const logger = createServerLogger("api.auth.mfa.setup");

/** The POST handler for the MFA setup API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:setup",
  telemetry: "api.auth.mfa.setup",
})(async (_req, { supabase }) => {
  try {
    const adminSupabase = getAdminSupabase();
    const enrollment = await startTotpEnrollment(supabase, { adminSupabase });
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
    let userId: string | null = null;
    try {
      const { data } = await supabase.auth.getUser();
      userId = data.user?.id ?? null;
    } catch {
      userId = null;
    }
    logger.error("mfa setup failed", {
      error: error instanceof Error ? error.message : "unknown_error",
      userId,
    });
    return NextResponse.json({ error: "mfa_setup_failed" }, { status: 500 });
  }
});
