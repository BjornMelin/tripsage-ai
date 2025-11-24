/**
 * @fileoverview Lightweight Google Places client helpers for server-side calls.
 */

import "server-only";

import { retryWithBackoff } from "@/lib/http/retry";

/**
 * Parameters for Google Places Text Search API request.
 */
type PlacesSearchParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Request body containing search query and options. */
  body: Record<string, unknown>;
  /** Field mask specifying which place fields to return. */
  fieldMask: string;
};

/**
 * Parameters for Google Places Details API request.
 */
type PlaceDetailsParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Field mask specifying which place fields to return. */
  fieldMask: string;
  /** Place ID to fetch details for. */
  placeId: string;
};

/**
 * Performs a text search against Google Places API with retry logic.
 *
 * @param params - Search parameters including API key, request body, and field mask.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function postPlacesSearch(params: PlacesSearchParams): Promise<Response> {
  return await retryWithBackoff(
    () =>
      fetch("https://places.googleapis.com/v1/places:searchText", {
        body: JSON.stringify(params.body),
        headers: {
          "Content-Type": "application/json",
          "X-Goog-Api-Key": params.apiKey,
          "X-Goog-FieldMask": params.fieldMask,
        },
        method: "POST",
      }),
    { attempts: 3, baseDelayMs: 200, maxDelayMs: 1_000 }
  );
}

/**
 * Fetches place details from Google Places API with retry logic.
 *
 * @param params - Details parameters including API key, place ID, and field mask.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function getPlaceDetails(params: PlaceDetailsParams): Promise<Response> {
  return await retryWithBackoff(
    () =>
      fetch(`https://places.googleapis.com/v1/${params.placeId}`, {
        headers: {
          "Content-Type": "application/json",
          "X-Goog-Api-Key": params.apiKey,
          "X-Goog-FieldMask": params.fieldMask,
        },
        method: "GET",
      }),
    { attempts: 3, baseDelayMs: 200, maxDelayMs: 1_000 }
  );
}
