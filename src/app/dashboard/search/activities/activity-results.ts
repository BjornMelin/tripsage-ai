/**
 * @fileoverview Helpers for partitioning activity results.
 */

import type { Activity } from "@schemas/search";

export const AI_FALLBACK_PREFIX = "ai_fallback:";

export function isActivity(data: unknown): data is Activity {
  return typeof data === "object" && data !== null && "id" in data && "name" in data;
}

export function partitionActivitiesByFallback(activities: Activity[]): {
  verifiedActivities: Activity[];
  aiSuggestions: Activity[];
  allAi: boolean;
} {
  const hasAi = activities.some((activity) =>
    activity.id.startsWith(AI_FALLBACK_PREFIX)
  );
  const hasNonAi = activities.some(
    (activity) => !activity.id.startsWith(AI_FALLBACK_PREFIX)
  );

  if (hasAi && hasNonAi) {
    return {
      aiSuggestions: activities.filter((activity) =>
        activity.id.startsWith(AI_FALLBACK_PREFIX)
      ),
      allAi: false,
      verifiedActivities: activities.filter(
        (activity) => !activity.id.startsWith(AI_FALLBACK_PREFIX)
      ),
    };
  }

  if (hasAi) {
    return {
      aiSuggestions: activities,
      allAi: true,
      verifiedActivities: [],
    };
  }

  return {
    aiSuggestions: [],
    allAi: false,
    verifiedActivities: activities,
  };
}
