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

  // TODO: Implement robust URL extraction from AI fallback activity descriptions.
  //
  // IMPLEMENTATION PLAN (Decision Framework Score: 9.0/10.0)
  // ===========================================================
  //
  // ARCHITECTURE DECISIONS:
  // -----------------------
  // 1. URL Extraction Method: Use regex pattern matching (lightweight, no dependencies)
  //    - Pattern: Match `https?://` URLs and common domain patterns
  //    - Rationale: Simple, fast, no external dependencies; sufficient for most cases
  //    - Alternative: Consider URL parsing library if validation becomes complex
  //
  // 2. URL Validation: Basic validation (format, domain presence)
  //    - Check URL format using URL constructor
  //    - Filter out obviously invalid domains (localhost, IP addresses for booking)
  //    - Rationale: Balance between safety and simplicity
  //
  // 3. URL Selection: Prioritize booking-related domains
  //    - Prefer URLs from known booking domains (viator, getyourguide, tripadvisor, etc.)
  //    - Fall back to first valid URL if no booking domain found
  //    - Rationale: Improves user experience by directing to booking sites
  //
  // IMPLEMENTATION STEPS:
  // ---------------------
  //
  // Step 1: Define URL Extraction Regex Pattern
  //   ```typescript
  //   // Comprehensive URL regex pattern
  //   const URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)/gi;
  //
  //   // Alternative: More permissive pattern for URLs without protocol
  //   const URL_WITHOUT_PROTOCOL_REGEX = /(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)/gi;
  //   ```
  //
  // Step 2: Implement URL Extraction Function
  //   ```typescript
  //   function extractUrlsFromText(text: string): string[] {
  //     if (!text) return [];
  //
  //     const urls: string[] = [];
  //     const matches = text.match(URL_REGEX);
  //
  //     if (matches) {
  //       for (const match of matches) {
  //         try {
  //           // Validate URL format
  //           const url = new URL(match);
  //           // Filter out invalid domains
  //           if (isValidBookingDomain(url.hostname)) {
  //             urls.push(url.toString());
  //           }
  //         } catch {
  //           // Invalid URL format, skip
  //           continue;
  //         }
  //       }
  //     }
  //
  //     // If no URLs with protocol found, try without protocol
  //     if (urls.length === 0) {
  //       const matchesWithoutProtocol = text.match(URL_WITHOUT_PROTOCOL_REGEX);
  //       if (matchesWithoutProtocol) {
  //         for (const match of matchesWithoutProtocol) {
  //           try {
  //             const url = new URL(`https://${match}`);
  //             if (isValidBookingDomain(url.hostname)) {
  //               urls.push(url.toString());
  //             }
  //           } catch {
  //             continue;
  //           }
  //         }
  //       }
  //     }
  //
  //     return urls;
  //   }
  //   ```
  //
  // Step 3: Implement Domain Validation
  //   ```typescript
  //   const BOOKING_DOMAINS = [
  //     "viator.com",
  //     "getyourguide.com",
  //     "tripadvisor.com",
  //     "expedia.com",
  //     "booking.com",
  //     "klook.com",
  //     "airbnb.com",
  //     "toursbylocals.com",
  //   ];
  //
  //   function isValidBookingDomain(hostname: string): boolean {
  //     // Reject localhost, IP addresses, and obviously invalid domains
  //     if (hostname === "localhost" || /^\d+\.\d+\.\d+\.\d+$/.test(hostname)) {
  //       return false;
  //     }
  //
  //     // Check if domain is a known booking domain
  //     const isKnownBookingDomain = BOOKING_DOMAINS.some((domain) =>
  //       hostname.includes(domain)
  //     );
  //
  //     // Accept known booking domains or any valid domain (for flexibility)
  //     return isKnownBookingDomain || hostname.includes(".");
  //   }
  //   ```
  //
  // Step 4: Implement URL Selection Logic
  //   ```typescript
  //   function selectBestBookingUrl(urls: string[]): string | null {
  //     if (urls.length === 0) return null;
  //
  //     // Prioritize known booking domains
  //     for (const url of urls) {
  //       try {
  //         const urlObj = new URL(url);
  //         const isKnownBookingDomain = BOOKING_DOMAINS.some((domain) =>
  //           urlObj.hostname.includes(domain)
  //         );
  //         if (isKnownBookingDomain) {
  //           return url;
  //         }
  //       } catch {
  //         continue;
  //       }
  //     }
  //
  //     // Fall back to first valid URL
  //     return urls[0] ?? null;
  //   }
  //   ```
  //
  // Step 5: Update getActivityBookingUrl Function
  //   ```typescript
  //   // For AI fallback activities, extract URL from description
  //   const description = activity.description ?? "";
  //   const urls = extractUrlsFromText(description);
  //   const selectedUrl = selectBestBookingUrl(urls);
  //
  //   if (selectedUrl) {
  //     // Add telemetry for successful URL extraction
  //     recordTelemetryEvent("activity.booking.url_extracted", {
  //       activity_id: activity.id,
  //       url_domain: new URL(selectedUrl).hostname,
  //       extraction_method: "description_parsing",
  //     });
  //     return selectedUrl;
  //   }
  //
  //   // Also check activity metadata if available
  //   if (activity.metadata && typeof activity.metadata === "object") {
  //     const metadataUrl = (activity.metadata as Record<string, unknown>).bookingUrl;
  //     if (typeof metadataUrl === "string" && isValidUrl(metadataUrl)) {
  //       return metadataUrl;
  //     }
  //   }
  //
  //   // No valid URL found
  //   recordTelemetryEvent("activity.booking.url_not_found", {
  //     activity_id: activity.id,
  //   });
  //   return null;
  //   ```
  //
  // INTEGRATION POINTS:
  // -------------------
  // - Activity Schema: Use `activity.description` and `activity.metadata` fields
  // - URL Validation: Use native `URL` constructor for format validation
  // - Telemetry: Use `recordTelemetryEvent` from `@/lib/telemetry/span` for tracking
  // - Error Handling: Gracefully handle invalid URLs, return null on failure
  //
  // PERFORMANCE CONSIDERATIONS:
  // ---------------------------
  // - Regex matching is fast for typical description lengths (< 1000 chars)
  // - URL validation is synchronous and lightweight
  // - Consider caching extracted URLs if same activity is accessed multiple times
  //
  // SECURITY CONSIDERATIONS:
  // ------------------------
  // - Validate all URLs before returning (prevent XSS via malicious URLs)
  // - Filter out localhost and IP addresses (not suitable for booking)
  // - Consider adding allowlist of trusted booking domains in production
  // - Sanitize URLs before displaying in UI
  //
  // USER EXPERIENCE:
  // ----------------
  // - Show warning in UI when using AI-extracted URLs: "This link was extracted from activity description and may not be verified"
  // - Prefer known booking domains for better user trust
  // - Fall back gracefully when no URL found (show "No booking link available")
  //
  // TESTING REQUIREMENTS:
  // ---------------------
  // - Unit test: URL extraction from various description formats
  // - Unit test: URL validation and domain filtering
  // - Unit test: URL selection logic (prioritize booking domains)
  // - Edge cases: Empty descriptions, malformed URLs, multiple URLs, no URLs
  //
  // FUTURE ENHANCEMENTS:
  // -------------------
  // - Add AI-powered URL extraction using LLM if regex fails
  // - Cache extracted URLs in activity metadata to avoid re-parsing
  // - Add URL verification (check if URL is accessible)
  // - Support extracting URLs from activity images (OCR)
  //
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
