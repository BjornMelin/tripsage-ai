import "server-only";

import type { MfaFactor } from "@schemas/mfa";
import { redirect } from "next/navigation";
import { MfaPanel } from "@/components/features/security/mfa-panel";
import { listFactors, refreshAal } from "@/lib/security/mfa";
import { getCurrentUser } from "@/lib/supabase/factory";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("app.security.page");

export default async function SecurityPage() {
  const supabase = await createServerSupabase();
  const { user } = await getCurrentUser(supabase);
  if (!user) {
    redirect("/login");
  }

  let aal: "aal1" | "aal2" = "aal1";
  let factors: MfaFactor[] = [];
  try {
    [aal, factors] = await Promise.all([refreshAal(supabase), listFactors(supabase)]);
  } catch (error) {
    logger.error("failed to load MFA data", {
      error: error instanceof Error ? error.message : "unknown_error",
    });
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <MfaPanel userEmail={user.email ?? ""} initialAal={aal} factors={factors} />
    </div>
  );
}
