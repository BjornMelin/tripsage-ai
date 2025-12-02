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
  try {
    [aal, factors] = await Promise.all([refreshAal(supabase), listFactors(supabase)]);
  } catch (error) {
    loadError = error instanceof Error ? error.message : "failed to load MFA data";
    logger.error("failed to load MFA data", {
      error: error instanceof Error ? error.message : "unknown_error",
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
