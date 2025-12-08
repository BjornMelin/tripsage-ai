/**
 * @fileoverview The API route for setting up MFA.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { startTotpEnrollment } from "@/lib/security/mfa";
import { classifyMfaError, logMfaError } from "@/lib/security/mfa-error";
import { getAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for setting up MFA. */
export const dynamic = "force-dynamic";

const logger = createServerLogger("api.auth.mfa.setup", {
  redactKeys: ["qrCode", "uri"],
});

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
      const { data, error: userError } = await supabase.auth.getUser();
      if (userError) {
        logger.error("failed to fetch user during mfa setup error handling", {
          error: userError.message,
        });
      }
      userId = data?.user?.id ?? null;
    } catch (getUserError) {
      logger.error("exception while fetching user for mfa setup classification", {
        error: getUserError instanceof Error ? getUserError.message : "unknown_error",
      });
    }
    const classification = classifyMfaError(error, "mfa_setup_failed");
    logMfaError(logger, error, { operation: "setup", userId }, "mfa_setup_failed");
    return errorResponse({
      err: classification.reason,
      error: classification.code,
      reason: classification.reason,
      status: classification.status,
    });
  }
});
