/**
 * @fileoverview The API route for listing MFA factors.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { listFactors, refreshAal } from "@/lib/security/mfa";
import { createServerLogger } from "@/lib/telemetry/logger";

/** The dynamic route for listing MFA factors. */
export const dynamic = "force-dynamic";

/** The logger for the MFA factors list API. */
const logger = createServerLogger("api.auth.mfa.factors.list");

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
  } catch (error) {
    logger.error("failed to list factors", {
      error: error instanceof Error ? error.message : "unknown_error",
      error_stack: error instanceof Error ? (error.stack ?? "no_stack") : String(error),
    });
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
});
