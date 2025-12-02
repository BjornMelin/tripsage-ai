import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { listFactors, refreshAal } from "@/lib/security/mfa";
import { createServerLogger } from "@/lib/telemetry/logger";

export const dynamic = "force-dynamic";
const logger = createServerLogger("api.auth.mfa.factors.list");

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
    });
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
});
