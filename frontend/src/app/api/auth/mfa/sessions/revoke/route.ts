/**
 * @fileoverview The API route handler for revoking MFA sessions.
 */

import "server-only";

import { mfaSessionRevokeInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, forbiddenResponse } from "@/lib/api/route-helpers";
import { MfaRequiredError, requireAal2, revokeSessions } from "@/lib/security/mfa";
import { classifyMfaError, logMfaError } from "@/lib/security/mfa-error";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for the MFA sessions revoke API. */
export const dynamic = "force-dynamic";

const logger = createServerLogger("api.auth.mfa.sessions.revoke", {
  redactKeys: ["userId", "scope"],
});

/** The POST handler for the MFA sessions revoke API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:sessions:revoke",
  schema: mfaSessionRevokeInputSchema,
  telemetry: "api.auth.mfa.sessions.revoke",
})(async (_req, { supabase }, data) => {
  try {
    await requireAal2(supabase);
    await revokeSessions(supabase, data.scope);
    logger.info("mfa sessions revoked", { scope: data.scope });
    return NextResponse.json({ data: { status: "revoked" } });
  } catch (error) {
    if (
      error instanceof MfaRequiredError ||
      (error as { code?: string } | null)?.code === "MFA_REQUIRED"
    ) {
      return forbiddenResponse("MFA verification required to revoke sessions");
    }
    const classification = classifyMfaError(error, "mfa_sessions_revoke_failed");
    logMfaError(
      logger,
      error,
      { operation: "sessions:revoke" },
      "mfa_sessions_revoke_failed"
    );
    return errorResponse({
      err: classification.reason,
      error: classification.code,
      reason: "Failed to revoke sessions",
      status: classification.status,
    });
  }
});
