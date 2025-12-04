/**
 * @fileoverview Accommodation search API route.
 *
 * POST /api/accommodations/search
 * Searches for accommodations using Amadeus provider with Places enrichment.
 */

import "server-only";

import { getAccommodationsService } from "@domain/accommodations/container";
import { accommodationSearchInputSchema } from "@schemas/accommodations";
import { withApiGuards } from "@/lib/api/factory";
import { getCurrentUser } from "@/lib/supabase/factory";

export const POST = withApiGuards({
  auth: false, // Allow anonymous searches
  rateLimit: "accommodations:search",
  schema: accommodationSearchInputSchema,
  telemetry: "accommodations.search",
})(async (_req, { supabase }, body) => {
  const userResult = await getCurrentUser(supabase);
  const service = getAccommodationsService();

  const result = await service.search(body, {
    rateLimitKey: userResult.user?.id ?? undefined,
    userId: userResult.user?.id ?? undefined,
  });

  return Response.json(result);
});
