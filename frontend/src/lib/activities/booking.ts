/**
 * @fileoverview Activity booking helpers.
 *
 * Provides external booking link resolution and minimal booking flow support.
 * Per SPEC-0030 Phase 4: no partner/approval-based APIs, external links only.
 */

import type { Activity } from "@schemas/search";

/**
 * Resolves an external booking URL for an activity.
 *
 * For Google Places activities, returns Google Maps place URL.
 * For AI fallback activities, attempts to extract URL from activity data.
 *
 * @param activity - Activity to get booking URL for.
 * @returns External booking URL or null if unavailable.
 */
export function getActivityBookingUrl(activity: Activity): string | null {
  // For Google Places activities, use Google Maps URL
  if (!activity.id.startsWith("ai_fallback:")) {
    // Google Maps place URL format: https://www.google.com/maps/place/?q=place_id:{placeId}
    return `https://www.google.com/maps/place/?q=place_id:${activity.id}`;
  }

  // For AI fallback, try to extract URL from description or return null
  // (AI fallback activities don't have reliable booking URLs)
  return null;
}

/**
 * Opens external booking link for an activity.
 *
 * @param activity - Activity to book.
 * @returns True if URL was opened, false if unavailable.
 */
export function openActivityBooking(activity: Activity): boolean {
  const url = getActivityBookingUrl(activity);
  if (!url) {
    return false;
  }

  // Open in new tab
  window.open(url, "_blank", "noopener,noreferrer");
  return true;
}
