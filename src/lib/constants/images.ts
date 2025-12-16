/**
 * @fileoverview Shared image constants used across the application.
 */

/**
 * Public fallback image URL/path for hotel listings.
 *
 * `NEXT_PUBLIC_*` values are inlined at build time (not read at runtime). This module
 * trims the inlined `NEXT_PUBLIC_FALLBACK_HOTEL_IMAGE` value and falls back to
 * `"/globe.svg"` when not provided. Expected format is a public URL or a public path.
 */
export const FALLBACK_HOTEL_IMAGE =
  process.env.NEXT_PUBLIC_FALLBACK_HOTEL_IMAGE?.trim() || "/globe.svg";
