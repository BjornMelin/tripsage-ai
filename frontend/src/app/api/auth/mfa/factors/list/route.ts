/**
 * @fileoverview The API route for listing MFA factors.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { listFactors, refreshAal } from "@/lib/security/mfa";
import { classifyMfaError, logMfaError } from "@/lib/security/mfa-error";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for listing MFA factors. */
export const dynamic = "force-dynamic";

const logger = createServerLogger("api.auth.mfa.factors.list", {
  redactKeys: ["userId", "factorId", "challengeId"],
});

/** The GET handler for the MFA factors list API. */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:factors:list",
  telemetry: "api.auth.mfa.factors.list",
})(async (_req, { supabase }) => {
  try {
    const [factors, aal] = await Promise.all([
      listFactors(supabase),
      refreshAal(supabase),
    ]);
    return NextResponse.json({ data: { aal, factors } });
  } catch (error: unknown) {
    const classification = classifyMfaError(error, "mfa_factors_list_failed");
    logMfaError(
      logger,
      error,
      { operation: "factors:list" },
      "mfa_factors_list_failed"
    );
    return errorResponse({
      err: classification.reason,
      error: classification.code,
      reason: "Failed to list MFA factors",
      status: classification.status,
    });
  }
});
