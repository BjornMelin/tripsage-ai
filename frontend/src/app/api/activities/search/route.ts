/**
 * @fileoverview Activity search API route.
 *
 * POST /api/activities/search
 * Searches for activities using Google Places API with optional AI fallback.
 */

import "server-only";

import { getActivitiesService } from "@domain/activities/container";
import { activitySearchParamsSchema } from "@schemas/search";
import { withApiGuards } from "@/lib/api/factory";
import { getCurrentUser } from "@/lib/supabase/factory";

export const POST = withApiGuards({
  auth: false, // Allow anonymous searches
  rateLimit: "activities:search",
  schema: activitySearchParamsSchema,
  telemetry: "activities.search",
})(async (_req, { supabase }, body) => {
  const userResult = await getCurrentUser(supabase);
  const service = getActivitiesService();

  const result = await service.search(body, {
    userId: userResult.user?.id ?? undefined,
    // IP and locale can be extracted from request headers if needed
  });

  return Response.json(result);
});
