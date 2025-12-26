/**
 * @fileoverview Dependency container for activities domain.
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
