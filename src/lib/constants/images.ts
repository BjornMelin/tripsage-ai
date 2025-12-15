/**
 * @fileoverview Shared image constants used across the application.
 */

/**
 * Public fallback image URL/path for hotel listings.
 *
 * Reads `NEXT_PUBLIC_FALLBACK_HOTEL_IMAGE` (trimmed) and falls back to `"/globe.svg"`
 * when not provided. Expected format is a public URL or a public path.
 */
export const FALLBACK_HOTEL_IMAGE =
  process.env.NEXT_PUBLIC_FALLBACK_HOTEL_IMAGE?.trim() || "/globe.svg";
