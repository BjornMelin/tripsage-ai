/**
 * @fileoverview Google Maps Platform API key management.
 *
 * Validates and loads server-side and browser API keys with restricted usage
 * guidance. Server keys must be IP+API restricted; browser keys must be HTTP
 * referrer-restricted to Maps JS only.
 */

import "server-only";

/**
 * Load and validate Google Maps Platform server API key.
 *
 * Server key must be IP+API restricted for Places, Routes, Geocoding, Time Zone.
 * Throws if key is missing or invalid.
 *
 * @returns Server API key.
 * @throws Error if key is missing or invalid.
 */
export function getGoogleMapsServerKey(): string {
  const key =
    typeof process !== "undefined" &&
    process.env &&
    process.env.GOOGLE_MAPS_SERVER_API_KEY
      ? process.env.GOOGLE_MAPS_SERVER_API_KEY
      : undefined;

  if (!key || key === "undefined") {
    throw new Error(
      "GOOGLE_MAPS_SERVER_API_KEY is required for Google Maps Platform services"
    );
  }

  return key;
}

/**
 * Load and validate Google Maps Platform browser API key.
 *
 * Browser key must be HTTP referrer-restricted to Maps JS only.
 * Returns undefined if key is not configured (client-side usage may be optional).
 *
 * @returns Browser API key or undefined.
 */
export function getGoogleMapsBrowserKey(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  // Browser key should be provided via NEXT_PUBLIC_ env var or runtime config
  // For now, we'll read from server env and pass to client via props/config
  return undefined;
}

/**
 * Validate that required Google Maps Platform keys are configured.
 *
 * @throws Error if server key is missing.
 */
export function validateGoogleMapsKeys(): void {
  getGoogleMapsServerKey();
}
