/**
 * @fileoverview POST /api/accommodations/search route handler.
 */

import "server-only";

import { getAccommodationsService } from "@domain/accommodations/container";
import { accommodationSearchInputSchema } from "@schemas/accommodations";
import { withApiGuards } from "@/lib/api/factory";
import { getCurrentUser } from "@/lib/supabase/server";

export const POST = withApiGuards({
  auth: false, // Allow anonymous searches
  rateLimit: "accommodations:search",
  schema: accommodationSearchInputSchema,
  telemetry: "accommodations.search",
})(async (_req, { supabase }, body) => {
  const userResult = await getCurrentUser(supabase);
  const service = getAccommodationsService();

  const result = await service.search(body, {
    userId: userResult.user?.id ?? undefined,
  });

  return Response.json(result);
});
