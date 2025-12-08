/**
 * @fileoverview The security page for the dashboard.
 */

import "server-only";

import type { MfaFactor } from "@schemas/mfa";
import { redirect } from "next/navigation";
import { MfaPanel } from "@/components/features/security/mfa-panel";
import { listFactors, refreshAal } from "@/lib/security/mfa";
import { getCurrentUser } from "@/lib/supabase/factory";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("app.security.page");

/** The security page for the dashboard. */
export default async function SecurityPage() {
  const supabase = await createServerSupabase();
  const { user } = await getCurrentUser(supabase);
  if (!user) {
    redirect("/login");
  }

  /** The authentication level. */
  let aal: "aal1" | "aal2" = "aal1";
  /** The MFA factors. */
  let factors: MfaFactor[] = [];
  /** The load error. */
  let loadError: string | null = null;
  const [aalResult, factorsResult] = await Promise.allSettled([
    refreshAal(supabase),
    listFactors(supabase),
  ]);

  if (aalResult.status === "fulfilled") {
    aal = aalResult.value;
  } else {
    const reason = aalResult.reason;
    const message =
      reason instanceof Error ? reason.message : "failed to load MFA assurance level";
    loadError = message;
    logger.error("failed to refresh MFA assurance level", {
      error: reason instanceof Error ? reason.message : "unknown_error",
    });
  }

  if (factorsResult.status === "fulfilled") {
    factors = factorsResult.value;
  } else {
    const reason = factorsResult.reason;
    const message =
      reason instanceof Error ? reason.message : "failed to load MFA factors";
    loadError = loadError ?? message;
    logger.error("failed to load MFA factors", {
      error: reason instanceof Error ? reason.message : "unknown_error",
    });
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <MfaPanel
        factors={factors}
        initialAal={aal}
        loadError={loadError}
        userEmail={user.email ?? ""}
      />
    </div>
  );
}
