/**
 * @fileoverview Dashboard security page (MFA settings).
 */

import "server-only";

import type { MfaFactor } from "@schemas/mfa";
import { redirect } from "next/navigation";
import { MfaPanel } from "@/components/features/security/mfa-panel";
import { SecurityDashboard } from "@/components/features/security/security-dashboard";
import { getUnknownErrorMessage } from "@/lib/errors/get-unknown-error-message";
import { ROUTES } from "@/lib/routes";
import { listFactors, refreshAal } from "@/lib/security/mfa";
import { getCurrentSessionId } from "@/lib/security/sessions";
import { createServerSupabase, getCurrentUser } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("app.security.page");

/** The security page for the dashboard. */
export default async function SecurityPage() {
  const supabase = await createServerSupabase();
  const { user } = await getCurrentUser(supabase);
  if (!user) {
    redirect(ROUTES.login);
  }

  let aal: "aal1" | "aal2" = "aal1";
  let factors: MfaFactor[] = [];
  let loadError: string | null = null;
  let currentSessionId: string | null = null;

  const [aalResult, factorsResult, currentSessionIdResult] = await Promise.allSettled([
    refreshAal(supabase),
    listFactors(supabase),
    getCurrentSessionId(supabase),
  ]);

  if (aalResult.status === "fulfilled") {
    aal = aalResult.value;
  } else {
    const reason = aalResult.reason;
    const message = getUnknownErrorMessage(
      reason,
      "failed to load MFA assurance level"
    );
    loadError = loadError ? `${loadError}\n${message}` : message;
    const safeError = reason instanceof Error ? reason : new Error(String(reason));
    logger.error("failed to refresh MFA assurance level", {
      error: safeError,
    });
  }

  if (factorsResult.status === "fulfilled") {
    factors = factorsResult.value;
  } else {
    const reason = factorsResult.reason;
    const message = getUnknownErrorMessage(reason, "failed to load MFA factors");
    loadError = loadError ? `${loadError}\n${message}` : message;
    const safeError = reason instanceof Error ? reason : new Error(String(reason));
    logger.error("failed to load MFA factors", {
      error: safeError,
    });
  }

  if (currentSessionIdResult.status === "fulfilled") {
    currentSessionId = currentSessionIdResult.value;
  } else {
    const reason = currentSessionIdResult.reason;
    const message = getUnknownErrorMessage(reason, "failed to load current session id");
    loadError = loadError ? `${loadError}\n${message}` : message;
    const safeError = reason instanceof Error ? reason : new Error(String(reason));
    logger.error("failed to load current session id", {
      error: safeError,
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
      <SecurityDashboard userId={user.id} currentSessionId={currentSessionId} />
    </div>
  );
}
