/**
 * @fileoverview The API route for issuing a MFA challenge.
 */

import "server-only";

import { mfaChallengeInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { challengeTotp } from "@/lib/security/mfa";
import { classifyMfaError, logMfaError } from "@/lib/security/mfa-error";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for the MFA challenge API. */
export const dynamic = "force-dynamic";

const logger = createServerLogger("api.auth.mfa.challenge", {
  redactKeys: ["factorId", "userId"],
});

/** The POST handler for the MFA challenge API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:challenge",
  schema: mfaChallengeInputSchema,
  telemetry: "api.auth.mfa.challenge",
})(async (_req, { supabase }, data) => {
  try {
    const result = await challengeTotp(supabase, { factorId: data.factorId });
    return NextResponse.json({ data: result });
  } catch (error) {
    const classification = classifyMfaError(error, "mfa_challenge_failed");
    logMfaError(
      logger,
      error,
      {
        factorId: data.factorId,
        operation: "challenge",
      },
      "mfa_challenge_failed"
    );
    return errorResponse({
      err: error,
      error: classification.code,
      reason: classification.reason,
      status: classification.status,
    });
  }
});
