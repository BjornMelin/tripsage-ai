/**
 * @fileoverview Activity booking helpers.
 *
 * Provides external booking link resolution and minimal booking flow support.
 */

import type { Activity } from "@schemas/search";

/** Structured attributes carried with booking telemetry events. */
type TelemetryAttributes = Record<string, string | number | boolean>;

/** Known booking domains to prioritize in URL extraction. */
const BOOKING_DOMAINS = [
  "airbnb.com",
  "booking.com",
  "expedia.com",
  "getyourguide.com",
  "klook.com",
  "orbitz.com",
  "priceline.com",
  "toursbylocals.com",
  "travelocity.com",
  "tripadvisor.com",
  "viator.com",
] as const;

/** Regular expression to match valid HTTP/HTTPS URLs. */
const URL_PATTERN = /https?:\/\/[^\s<>"']+/gi;

/** Activity type with optional metadata field. */
type ActivityWithMetadata = Activity & { metadata?: unknown };

/**
 * Return true when hostname is an IPv4/IPv6 literal (blocks all IP-based hosts).
 *
 * @param hostname Hostname string from a parsed URL.
 * @returns True if hostname is any IP literal.
 */
function isIpAddressHost(hostname: string): boolean {
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(hostname)) {
    return true;
  }
  // IPv6 (plain or bracketed)
  if (/^\[?[0-9a-f:]+\]?$/i.test(hostname)) {
    return true;
  }
  return false;
}

/**
 * Validate a URL string and return a URL object if valid.
 *
 * @param candidate URL string to validate.
 * @returns URL object if valid, null otherwise.
 */
function validateUrl(candidate: string): URL | null {
  try {
    const parsed = new URL(candidate);
    const { protocol, hostname } = parsed;

    if (protocol !== "http:" && protocol !== "https:") return null;
    if (hostname === "localhost" || hostname.endsWith(".local")) return null;
    if (isIpAddressHost(hostname)) return null;

    return parsed;
  } catch {
    return null;
  }
}

/**
 * Return true if hostname matches a known booking domain or its subdomain.
 *
 * @param hostname Hostname to evaluate.
 * @returns True when hostname is within the booking allowlist.
 */
function hasKnownBookingDomain(hostname: string): boolean {
  const normalized = hostname.toLowerCase().replace(/\.$/, "");
  return BOOKING_DOMAINS.some((domain) => {
    const normalizedDomain = domain.toLowerCase();
    return (
      normalized === normalizedDomain || normalized.endsWith(`.${normalizedDomain}`)
    );
  });
}

/**
 * Extract valid http/https URLs from freeform text.
 *
 * @param text Source text to scan.
 * @returns Array of normalized URLs.
 */
function extractUrlsFromText(text?: string): string[] {
  if (!text) return [];
  const matches = text.match(URL_PATTERN);
  if (!matches) return [];

  const seen = new Set<string>();
  for (const raw of matches) {
    const parsed = validateUrl(raw);
    if (parsed) {
      const normalized = parsed.toString();
      if (!seen.has(normalized)) {
        seen.add(normalized);
      }
    }
  }

  return Array.from(seen);
}

/**
 * Extract and validate a booking-like URL from activity metadata.
 *
 * @param metadata Activity metadata object.
 * @returns First valid URL or null.
 */
function extractMetadataUrl(metadata: unknown): string | null {
  if (!metadata || typeof metadata !== "object") return null;
  const record = metadata as Record<string, unknown>;
  const candidates = [
    record.bookingUrl,
    record.url,
    record.link,
    record.website,
  ].filter((value): value is string => typeof value === "string" && value.length > 0);

  for (const candidate of candidates) {
    const parsed = validateUrl(candidate);
    if (parsed) {
      return parsed.toString();
    }
  }
  return null;
}

/**
 * Choose best URL preferring known booking hosts; fall back to first valid.
 *
 * @param candidates Candidate URL strings.
 * @returns Selected URL or null.
 */
function pickBestUrl(candidates: string[]): string | null {
  const valid = candidates.map(validateUrl).filter((url): url is URL => url !== null);

  if (valid.length === 0) return null;

  const prioritized = valid.find((url) => hasKnownBookingDomain(url.hostname));
  return (prioritized ?? valid[0]).toString();
}

/**
 * Build a Google Maps search URL from coordinates or name/location as fallback.
 *
 * @param activity Activity containing coordinates or name/location.
 * @returns A Google Maps search URL or null.
 */
function buildMapSearchUrl(activity: ActivityWithMetadata): string | null {
  if (activity.coordinates) {
    const { lat, lng } = activity.coordinates;
    return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  }

  const queryParts: string[] = [];
  if (activity.name) queryParts.push(activity.name);
  if (activity.location) queryParts.push(activity.location);
  if (!queryParts.length) return null;

  const query = encodeURIComponent(queryParts.join(" "));
  return `https://www.google.com/maps/search/?api=1&query=${query}`;
}

/** Emit booking telemetry (client via beacon/fetch, server via OTEL). */
async function recordBookingEvent(
  eventName: string,
  attributes?: TelemetryAttributes,
  level: "info" | "warning" | "error" = "info"
): Promise<void> {
  // Client: fire-and-forget to telemetry endpoint to capture real user clicks.
  if (typeof window !== "undefined") {
    try {
      const payload = JSON.stringify({ attributes, eventName, level });
      if (
        typeof navigator !== "undefined" &&
        typeof navigator.sendBeacon === "function"
      ) {
        navigator.sendBeacon("/api/telemetry/activities", payload);
      } else {
        fetch("/api/telemetry/activities", {
          body: payload,
          headers: { "Content-Type": "application/json" },
          keepalive: true,
          method: "POST",
        }).catch(() => undefined);
      }
    } catch {
      // Client telemetry is best-effort; ignore failures.
    }
    return;
  }

  // Server: record span-based telemetry.
  try {
    const telemetry = await import("@/lib/telemetry/span");
    telemetry.recordTelemetryEvent(eventName, { attributes, level });
  } catch {
    // Telemetry is best-effort; swallow errors to avoid impacting runtime.
  }
}

/**
 * Resolves an external booking URL for an activity.
 *
 * For Google Places activities, returns Google Maps place URL.
 * For AI fallback activities, attempts to extract URL from activity data.
 *
 * @param activity - Activity to get booking URL for.
 * @returns External booking URL or null if unavailable.
 */
export function getActivityBookingUrl(activity: ActivityWithMetadata): string | null {
  if (!activity.id.startsWith("ai_fallback:")) {
    const url = `https://www.google.com/maps/place/?q=place_id:${activity.id}`;
    recordBookingEvent("activities.booking.url_resolved", {
      activityId: activity.id,
      domain: "google.com",
      method: "place_id",
    }).catch(() => {
      /* telemetry is best-effort */
    });
    return url;
  }

  const metadataUrl = extractMetadataUrl(activity.metadata);
  const descriptionUrls = extractUrlsFromText(activity.description);
  const bestUrl = pickBestUrl(
    [metadataUrl, ...descriptionUrls].filter(
      (url): url is string => typeof url === "string"
    )
  );

  if (bestUrl) {
    const domain = validateUrl(bestUrl)?.hostname ?? "unknown";
    recordBookingEvent("activities.booking.url_resolved", {
      activityId: activity.id,
      domain,
      method: "ai_extracted",
    }).catch(() => {
      /* telemetry is best-effort */
    });
    return bestUrl;
  }

  const mapFallback = buildMapSearchUrl(activity);
  if (mapFallback) {
    recordBookingEvent("activities.booking.url_resolved", {
      activityId: activity.id,
      domain: "google.com",
      method: "map_fallback",
    }).catch(() => {
      /* telemetry is best-effort */
    });
    return mapFallback;
  }

  recordBookingEvent(
    "activities.booking.url_missing",
    { activityId: activity.id },
    "warning"
  ).catch(() => {
    /* telemetry is best-effort */
  });
  return null;
}

/**
 * Opens external booking link for an activity.
 *
 * @param activity - Activity to book.
 * @returns True if URL was opened, false if unavailable.
 */
export function openActivityBooking(activity: ActivityWithMetadata): boolean {
  const url = getActivityBookingUrl(activity);
  if (!url || typeof window === "undefined") {
    return false;
  }

  window.open(url, "_blank", "noopener,noreferrer");
  return true;
}
