import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { challengeTotp } from "@/lib/security/mfa";

const schema = z.strictObject({
  factorId: z.string().uuid(),
});

export const dynamic = "force-dynamic";

export const POST = withApiGuards({
  auth: true,
  rateLimit: "auth:mfa:challenge",
  schema,
  telemetry: "api.auth.mfa.challenge",
})(async (_req, { supabase }, data) => {
  const result = await challengeTotp(supabase, { factorId: data.factorId });
  return NextResponse.json({ data: result });
});
