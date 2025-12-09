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
  const placeIdPattern = /^(places\/)?[A-Za-z0-9_-]+$/;
  if (!placeIdPattern.test(params.placeId)) {
    throw new Error(
      `Invalid placeId "${params.placeId}": must match pattern ${placeIdPattern}`
    );
  }

  if (!params.fieldMask || params.fieldMask.trim().length === 0) {
    throw new Error("fieldMask is required for place details");
  }

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

/**
 * Parameters for Google Places Nearby Search API request.
 */
type NearbySearchParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Field mask specifying which place fields to return. */
  fieldMask: string;
  /** Array of place type filters (e.g., ["tourist_attraction", "museum"]). */
  includedTypes?: string[];
  /** Latitude of the search center. */
  lat: number;
  /** Longitude of the search center. */
  lng: number;
  /** Maximum number of results to return (1-20). */
  maxResultCount?: number;
  /** Search radius in meters (max 50000). */
  radiusMeters?: number;
};

/**
 * Performs a nearby search against Google Places API with retry logic.
 *
 * @param params - Search parameters including coordinates, radius, and place types.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function postNearbySearch(params: NearbySearchParams): Promise<Response> {
  if (!Number.isFinite(params.lat) || params.lat < -90 || params.lat > 90) {
    throw new Error(
      `Invalid latitude "${params.lat}": must be a number between -90 and 90`
    );
  }

  if (!Number.isFinite(params.lng) || params.lng < -180 || params.lng > 180) {
    throw new Error(
      `Invalid longitude "${params.lng}": must be a number between -180 and 180`
    );
  }

  if (params.maxResultCount !== undefined) {
    if (
      !Number.isInteger(params.maxResultCount) ||
      params.maxResultCount < 1 ||
      params.maxResultCount > 20
    ) {
      throw new Error(
        `Invalid maxResultCount "${params.maxResultCount}": must be an integer between 1 and 20`
      );
    }
  }

  if (params.radiusMeters !== undefined) {
    if (
      !Number.isFinite(params.radiusMeters) ||
      params.radiusMeters <= 0 ||
      params.radiusMeters > 50_000
    ) {
      throw new Error(
        `Invalid radiusMeters "${params.radiusMeters}": must be a positive number <= 50000`
      );
    }
  }

  const body: Record<string, unknown> = {
    locationRestriction: {
      circle: {
        center: {
          latitude: params.lat,
          longitude: params.lng,
        },
        radius: params.radiusMeters ?? 1000,
      },
    },
    maxResultCount: params.maxResultCount ?? 10,
  };

  if (params.includedTypes?.length) {
    body.includedTypes = params.includedTypes;
  }

  return await retryWithBackoff(
    () =>
      fetch("https://places.googleapis.com/v1/places:searchNearby", {
        body: JSON.stringify(body),
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
