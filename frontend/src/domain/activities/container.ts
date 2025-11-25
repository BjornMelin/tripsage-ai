/**
 * @fileoverview Dependency container for activities domain.
 *
 * Centralizes construction of the activities service so callers (AI tools, routes)
 * do not hard-wire dependencies at import time.
 */

import { ActivitiesService } from "@domain/activities/service";
import { createServerSupabase } from "@/lib/supabase/server";

let singleton: ActivitiesService | undefined;

/**
 * Returns a singleton ActivitiesService configured with Supabase factory.
 */
export function getActivitiesService(): ActivitiesService {
  if (singleton) return singleton;

  singleton = new ActivitiesService({
    supabase: createServerSupabase,
  });

  return singleton;
}
