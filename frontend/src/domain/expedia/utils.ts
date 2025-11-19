/**
 * @fileoverview Utility functions for Expedia Rapid API link parsing.
 *
 * Provides functions to extract booking tokens and expiration data from Rapid API
 * URLs and response objects.
 */

import type { RapidLink } from "@/domain/schemas/expedia";
import { ExpediaApiError } from "./client-types";
import { RAPID_PROD_DEFAULT_BASE_URL } from "./constants";

/**
 * Extracts booking token from Rapid API link.
 *
 * Parses the href URL and extracts the 'token' query parameter.
 * Throws ExpediaApiError if link is missing or token not found.
 *
 * @param link - Rapid API link object containing href URL.
 * @returns Extracted booking token string.
 * @throws {ExpediaApiError} When link or token is missing.
 */
export function extractTokenFromLink(link?: RapidLink): string {
  if (!link?.href) {
    throw new ExpediaApiError("Missing booking link", "EPS_BOOKING_LINK_MISSING", 409);
  }
  const baseUrl = link.href.startsWith("http")
    ? undefined
    : RAPID_PROD_DEFAULT_BASE_URL;
  const url = new URL(link.href, baseUrl);
  const token = url.searchParams.get("token");
  if (!token) {
    throw new ExpediaApiError(
      "Booking token missing from link",
      "EPS_TOKEN_MISSING",
      409
    );
  }
  return token;
}

/**
 * Extracts expiration timestamp from Rapid API link.
 *
 * Parses the href URL and extracts the 'expires_at' query parameter.
 * Returns undefined if link or parameter is missing.
 *
 * @param link - Rapid API link object containing href URL.
 * @returns Expiration timestamp string or undefined.
 */
export function extractExpiration(link?: RapidLink): string | undefined {
  if (!link?.href) {
    return undefined;
  }
  const baseUrl = link.href.startsWith("http")
    ? undefined
    : RAPID_PROD_DEFAULT_BASE_URL;
  const expirationParam = new URL(link.href, baseUrl);
  const expiry = expirationParam.searchParams.get("expires_at");
  return expiry ?? undefined;
}
