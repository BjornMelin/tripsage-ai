/**
 * @fileoverview The API route handler for revoking MFA sessions.
 */

import "server-only";

import { mfaSessionRevokeInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { MfaRequiredError, requireAal2, revokeSessions } from "@/lib/security/mfa";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for the MFA sessions revoke API. */
export const dynamic = "force-dynamic";
const logger = createServerLogger("api.auth.mfa.sessions.revoke");

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
    return NextResponse.json({ data: { status: "revoked" } });
  } catch (error) {
    if (
      error instanceof MfaRequiredError ||
      (error as { code?: string } | null)?.code === "MFA_REQUIRED"
    ) {
      return NextResponse.json({ error: "mfa_required" }, { status: 403 });
    }
    logger.error("failed to revoke sessions", {
      error: error instanceof Error ? error.message : "unknown_error",
    });
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
});
