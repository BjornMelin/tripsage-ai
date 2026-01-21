/**
 * @fileoverview POST /api/activities/search route handler.
 */

import "server-only";

import { webSearch } from "@ai/tools/server/web-search";
import { activitySearchParamsSchema } from "@schemas/search";
import {
  createActivitiesService,
  createWebSearchFallback,
} from "@/lib/activities/service-factory";
import { createSupabaseActivitiesSearchCache } from "@/lib/activities/supabase-cache";
import { withApiGuards } from "@/lib/api/factory";
import { getCurrentUser } from "@/lib/supabase/server";

export const POST = withApiGuards({
  auth: false, // Allow anonymous searches
  botId: true,
  rateLimit: "activities:search",
  schema: activitySearchParamsSchema,
  telemetry: "activities.search",
})(async (_req, { supabase }, body) => {
  const userResult = await getCurrentUser(supabase);

  const cache = createSupabaseActivitiesSearchCache(supabase);
  const fallbackWebSearch = createWebSearchFallback(webSearch.execute);
  const service = createActivitiesService({ cache, webSearch: fallbackWebSearch });

  const result = await service.search(body, {
    userId: userResult.user?.id ?? undefined,
    // IP and locale can be extracted from request headers if needed
  });

  return Response.json(result);
});
