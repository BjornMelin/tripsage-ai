/**
 * @fileoverview The API route for issuing a MFA challenge.
 */

import { mfaChallengeInputSchema } from "@schemas/mfa";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { challengeTotp } from "@/lib/security/mfa";

/** The dynamic route for the MFA challenge API. */
export const dynamic = "force-dynamic";

/** The POST handler for the MFA challenge API. */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:challenge",
  schema: mfaChallengeInputSchema,
  telemetry: "api.auth.mfa.challenge",
})(async (_req, { supabase }, data) => {
  const result = await challengeTotp(supabase, { factorId: data.factorId });
  return NextResponse.json({ data: result });
});
