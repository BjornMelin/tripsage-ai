/**
 * @fileoverview Centralized Google API client helpers for server-side calls.
 */

import "server-only";

import { retryWithBackoff } from "@/lib/http/retry";

// === Coordinate Validation ===

/**
 * Validates latitude and longitude coordinates.
 *
 * Throws descriptive errors if coordinates are invalid. Used by multiple
 * API functions to ensure consistent validation and error messages.
 *
 * @param lat - Latitude to validate (-90 to 90).
 * @param lng - Longitude to validate (-180 to 180).
 * @throws Error if coordinates are not finite numbers or out of valid range.
 */
function validateCoordinates(lat: number, lng: number): void {
  if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
    throw new Error(`Invalid latitude "${lat}": must be a number between -90 and 90`);
  }

  if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
    throw new Error(
      `Invalid longitude "${lng}": must be a number between -180 and 180`
    );
  }
}

// === NDJSON Helpers ===

/**
 * Parses a newline-delimited JSON (NDJSON) response body into an array of objects.
 *
 * Google Routes API computeRouteMatrix returns NDJSON streams where each line
 * is a separate JSON object, not a single JSON array. This helper reads the
 * response text and parses each non-empty line as JSON.
 *
 * @param response - Fetch Response object to parse.
 * @returns Promise resolving to array of parsed JSON objects.
 * @throws Error if any line fails to parse as JSON.
 */
export async function parseNdjsonResponse<T = unknown>(
  response: Response
): Promise<T[]> {
  const text = await response.text();
  const lines = text.split("\n").filter((line) => line.trim().length > 0);

  return lines.map((line, index) => {
    try {
      return JSON.parse(line) as T;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new Error(
        `Failed to parse NDJSON line ${index + 1}: ${message}. Line content: ${line.slice(0, 100)}...`
      );
    }
  });
}

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
  /** Session token for autocomplete session termination (optional). */
  sessionToken?: string;
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

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": params.apiKey,
    "X-Goog-FieldMask": params.fieldMask,
  };

  if (params.sessionToken) {
    headers["X-Goog-Session-Token"] = params.sessionToken;
  }

  return await retryWithBackoff(
    () =>
      fetch(`https://places.googleapis.com/v1/${params.placeId}`, {
        headers,
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

// === Routes API v2 ===

/**
 * Parameters for Google Routes API computeRoutes request.
 */
type ComputeRoutesParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Request body containing origin, destination, and options. */
  body: Record<string, unknown>;
  /** Field mask specifying which route fields to return. */
  fieldMask: string;
};

/**
 * Performs a computeRoutes request against Google Routes API with retry logic.
 *
 * @param params - Route parameters including API key, request body, and field mask.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function postComputeRoutes(
  params: ComputeRoutesParams
): Promise<Response> {
  if (!params.fieldMask || params.fieldMask.trim().length === 0) {
    throw new Error("fieldMask is required for computeRoutes");
  }

  return await retryWithBackoff(
    () =>
      fetch("https://routes.googleapis.com/directions/v2:computeRoutes", {
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
 * Parameters for Google Routes API computeRouteMatrix request.
 */
type ComputeRouteMatrixParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Request body containing origins, destinations, and options. */
  body: Record<string, unknown>;
  /** Field mask specifying which matrix fields to return. */
  fieldMask: string;
};

/**
 * Performs a computeRouteMatrix request against Google Routes API with retry logic.
 *
 * @param params - Matrix parameters including API key, request body, and field mask.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function postComputeRouteMatrix(
  params: ComputeRouteMatrixParams
): Promise<Response> {
  if (!params.fieldMask || params.fieldMask.trim().length === 0) {
    throw new Error("fieldMask is required for computeRouteMatrix");
  }

  return await retryWithBackoff(
    () =>
      fetch("https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix", {
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

// === Legacy Geocoding API ===

/**
 * Parameters for Google Geocoding API forward geocode request.
 */
type GeocodeParams = {
  /** Address string to geocode. */
  address: string;
  /** Google Maps API key for authentication. */
  apiKey: string;
};

/**
 * Performs forward geocoding against Google Geocoding API with retry logic.
 *
 * @param params - Geocode parameters including API key and address.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function getGeocode(params: GeocodeParams): Promise<Response> {
  // Validate address parameter
  const trimmedAddress = params.address.trim();
  if (!trimmedAddress) {
    throw new Error(
      "Invalid address: must be a non-empty string after trimming whitespace"
    );
  }

  const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
  url.searchParams.set("address", trimmedAddress);
  url.searchParams.set("key", params.apiKey);

  return await retryWithBackoff(() => fetch(url.toString(), { method: "GET" }), {
    attempts: 3,
    baseDelayMs: 200,
    maxDelayMs: 1_000,
  });
}

/**
 * Parameters for Google Geocoding API reverse geocode request.
 */
type ReverseGeocodeParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Latitude of the location to reverse geocode. */
  lat: number;
  /** Longitude of the location to reverse geocode. */
  lng: number;
};

/**
 * Performs reverse geocoding against Google Geocoding API with retry logic.
 *
 * @param params - Reverse geocode parameters including API key and coordinates.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function getReverseGeocode(
  params: ReverseGeocodeParams
): Promise<Response> {
  validateCoordinates(params.lat, params.lng);

  const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
  url.searchParams.set("latlng", `${params.lat},${params.lng}`);
  url.searchParams.set("key", params.apiKey);

  return await retryWithBackoff(() => fetch(url.toString(), { method: "GET" }), {
    attempts: 3,
    baseDelayMs: 200,
    maxDelayMs: 1_000,
  });
}

// === Legacy Timezone API ===

/**
 * Parameters for Google Timezone API request.
 */
type TimezoneParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Latitude of the location. */
  lat: number;
  /** Longitude of the location. */
  lng: number;
  /** Unix timestamp in seconds (defaults to current time). */
  timestamp?: number;
};

/**
 * Fetches timezone information from Google Timezone API with retry logic.
 *
 * @param params - Timezone parameters including API key, coordinates, and optional timestamp.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function getTimezone(params: TimezoneParams): Promise<Response> {
  validateCoordinates(params.lat, params.lng);

  const url = new URL("https://maps.googleapis.com/maps/api/timezone/json");
  url.searchParams.set("location", `${params.lat},${params.lng}`);
  url.searchParams.set(
    "timestamp",
    String(params.timestamp ?? Math.floor(Date.now() / 1000))
  );
  url.searchParams.set("key", params.apiKey);

  return await retryWithBackoff(() => fetch(url.toString(), { method: "GET" }), {
    attempts: 3,
    baseDelayMs: 200,
    maxDelayMs: 1_000,
  });
}

// === Places Photo API ===

/**
 * Parameters for Google Places API photo media request.
 */
type PlacePhotoParams = {
  /** Google Maps API key for authentication. */
  apiKey: string;
  /** Maximum height in pixels (optional). */
  maxHeightPx?: number;
  /** Maximum width in pixels (optional). */
  maxWidthPx?: number;
  /** Photo resource name (e.g., "places/ABC/photos/XYZ"). */
  photoName: string;
  /** If true, skip HTTP redirect and return photo URI instead (optional). */
  skipHttpRedirect?: boolean;
};

/**
 * Fetches place photo from Google Places API with retry logic.
 *
 * @param params - Photo parameters including API key, photo name, and optional dimensions.
 * @returns Promise resolving to the API response (photo bytes or redirect).
 * @throws Error if all retry attempts fail.
 */
export async function getPlacePhoto(params: PlacePhotoParams): Promise<Response> {
  const photoNamePattern = /^places\/[A-Za-z0-9_-]+\/photos\/[A-Za-z0-9_-]+$/;
  if (!photoNamePattern.test(params.photoName)) {
    throw new Error(
      `Invalid photoName "${params.photoName}": must match pattern places/{placeId}/photos/{photoId}`
    );
  }

  // Google Places Photo API requires at least one dimension parameter
  if (params.maxWidthPx === undefined && params.maxHeightPx === undefined) {
    throw new Error("Either maxWidthPx or maxHeightPx must be provided");
  }

  // Validate photo dimensions if provided (Google Places Photo API limit is 4800)
  const maxDimension = 4800;
  if (params.maxWidthPx !== undefined) {
    if (!Number.isFinite(params.maxWidthPx) || !Number.isInteger(params.maxWidthPx)) {
      throw new Error(
        `Invalid maxWidthPx "${params.maxWidthPx}": must be a finite integer`
      );
    }
    if (params.maxWidthPx <= 0) {
      throw new Error(
        `Invalid maxWidthPx "${params.maxWidthPx}": must be greater than 0`
      );
    }
    if (params.maxWidthPx > maxDimension) {
      throw new Error(
        `Invalid maxWidthPx "${params.maxWidthPx}": must not exceed ${maxDimension}`
      );
    }
  }

  if (params.maxHeightPx !== undefined) {
    if (!Number.isFinite(params.maxHeightPx) || !Number.isInteger(params.maxHeightPx)) {
      throw new Error(
        `Invalid maxHeightPx "${params.maxHeightPx}": must be a finite integer`
      );
    }
    if (params.maxHeightPx <= 0) {
      throw new Error(
        `Invalid maxHeightPx "${params.maxHeightPx}": must be greater than 0`
      );
    }
    if (params.maxHeightPx > maxDimension) {
      throw new Error(
        `Invalid maxHeightPx "${params.maxHeightPx}": must not exceed ${maxDimension}`
      );
    }
  }

  const url = new URL(`https://places.googleapis.com/v1/${params.photoName}/media`);
  if (params.maxWidthPx !== undefined) {
    url.searchParams.set("maxWidthPx", String(params.maxWidthPx));
  }
  if (params.maxHeightPx !== undefined) {
    url.searchParams.set("maxHeightPx", String(params.maxHeightPx));
  }
  if (params.skipHttpRedirect) {
    url.searchParams.set("skipHttpRedirect", "true");
  }

  const isAllowedRedirectHost = (candidate: URL): boolean => {
    if (candidate.protocol !== "https:") return false;
    const hostname = candidate.hostname.toLowerCase();
    return (
      hostname === "googleusercontent.com" ||
      hostname.endsWith(".googleusercontent.com")
    );
  };

  const initialResponse = await retryWithBackoff(
    () =>
      fetch(url.toString(), {
        headers: {
          "X-Goog-Api-Key": params.apiKey,
        },
        method: "GET",
        redirect: "manual",
      }),
    { attempts: 3, baseDelayMs: 200, maxDelayMs: 1_000 }
  );

  // Default Places photo media behavior is an HTTP redirect to an image host (googleusercontent).
  // Follow redirects manually to avoid leaking the API key header to the redirected request and
  // to enforce an explicit allowlist of redirect targets.
  if (initialResponse.status >= 300 && initialResponse.status < 400) {
    const location = initialResponse.headers.get("location");
    if (!location) {
      return initialResponse;
    }

    let nextUrl = new URL(location, url);
    const maxRedirects = 3;

    for (let hop = 0; hop < maxRedirects; hop += 1) {
      if (!isAllowedRedirectHost(nextUrl)) {
        throw new Error(`Unexpected Places photo redirect host: ${nextUrl.hostname}`);
      }

      // Do not forward the API key header to the redirected host.
      const redirectedResponse = await retryWithBackoff(
        () =>
          fetch(nextUrl.toString(), {
            method: "GET",
            redirect: "manual",
          }),
        { attempts: 3, baseDelayMs: 200, maxDelayMs: 1_000 }
      );

      if (redirectedResponse.status >= 300 && redirectedResponse.status < 400) {
        const redirectedLocation = redirectedResponse.headers.get("location");
        if (!redirectedLocation) {
          return redirectedResponse;
        }
        nextUrl = new URL(redirectedLocation, nextUrl);
        continue;
      }

      return redirectedResponse;
    }

    throw new Error("Places photo redirect limit exceeded");
  }

  return initialResponse;
}

// === Places Nearby Search API ===

/**
 * Performs a nearby search against Google Places API with retry logic.
 *
 * @param params - Search parameters including coordinates, radius, and place types.
 * @returns Promise resolving to the API response.
 * @throws Error if all retry attempts fail.
 */
export async function postNearbySearch(params: NearbySearchParams): Promise<Response> {
  validateCoordinates(params.lat, params.lng);

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
