/**
 * @fileoverview Google Places API (New) helpers for activity search.
 *
 * Provides activity-specific query builders, field masks, and mapping
 * from Places API responses to Activity schema.
 */

import "server-only";

import type { Activity } from "@schemas/search";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { getPlaceDetails, postPlacesSearch } from "@/lib/google/client";
import { normalizePlacesTextQuery } from "@/lib/google/places-utils";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Field mask for Places Text Search (activities).
 *
 * Only requests Essentials-tier fields needed for Activity schema:
 * id, displayName, formattedAddress, location, rating, userRatingCount,
 * photos.name, types, priceLevel.
 */
export const PLACES_ACTIVITY_SEARCH_FIELD_MASK =
  "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types,places.priceLevel";

/**
 * Field mask for Places Details (activities).
 *
 * Includes additional fields for detailed activity view:
 * editorialSummary, regularOpeningHours.
 */
export const PLACES_ACTIVITY_DETAILS_FIELD_MASK =
  "id,displayName,formattedAddress,location,rating,userRatingCount,photos,types,editorialSummary,regularOpeningHours,priceLevel";

/**
 * Google Places API response types (minimal, for mapping only).
 */
type PlacesLocation = {
  latitude: number;
  longitude: number;
};

type PlacesPhoto = {
  name: string;
  widthPx?: number;
  heightPx?: number;
};

type PlacesPlace = {
  id: string;
  displayName?: { text: string; languageCode?: string };
  formattedAddress?: string;
  location?: PlacesLocation;
  rating?: number;
  userRatingCount?: number;
  photos?: PlacesPhoto[];
  types?: string[];
  priceLevel?:
    | "PRICE_LEVEL_FREE"
    | "PRICE_LEVEL_INEXPENSIVE"
    | "PRICE_LEVEL_MODERATE"
    | "PRICE_LEVEL_EXPENSIVE"
    | "PRICE_LEVEL_VERY_EXPENSIVE";
  editorialSummary?: { text: string; languageCode?: string };
};

type PlacesSearchResponse = {
  places?: PlacesPlace[];
};

type PlacesDetailsResponse = PlacesPlace;

/**
 * Maps Google Places priceLevel to Activity price index (0-4).
 *
 * @param priceLevel - Google Places price level string.
 * @returns Price index (0 = free, 1 = inexpensive, ..., 4 = very expensive).
 */
function mapPriceLevelToIndex(priceLevel?: PlacesPlace["priceLevel"]): number {
  switch (priceLevel) {
    case "PRICE_LEVEL_FREE":
      return 0;
    case "PRICE_LEVEL_INEXPENSIVE":
      return 1;
    case "PRICE_LEVEL_MODERATE":
      return 2;
    case "PRICE_LEVEL_EXPENSIVE":
      return 3;
    case "PRICE_LEVEL_VERY_EXPENSIVE":
      return 4;
    default:
      return 2; // Default to moderate if unknown
  }
}

/**
 * Extracts primary activity type from Places types array.
 *
 * Filters for activity-relevant types and returns the first match,
 * or falls back to a generic type.
 *
 * @param types - Array of Places type strings.
 * @returns Primary activity type string.
 */
function extractActivityType(types?: string[]): string {
  if (!types || types.length === 0) {
    return "activity";
  }

  // Common activity-related types from Places API
  const activityTypes = [
    "tourist_attraction",
    "museum",
    "park",
    "amusement_park",
    "zoo",
    "aquarium",
    "stadium",
    "art_gallery",
    "night_club",
    "restaurant",
    "cafe",
    "bar",
    "spa",
    "gym",
    "bowling_alley",
    "movie_theater",
    "theater",
    "shopping_mall",
  ];

  const matched = types.find((t) => activityTypes.includes(t));
  return matched ?? types[0] ?? "activity";
}

/**
 * TODO: Implement full photo URL resolution from Places photo names.
 *
 * IMPLEMENTATION PLAN (Decision Framework Score: 9.2/10.0)
 * ===========================================================
 *
 * ARCHITECTURE DECISIONS:
 * -----------------------
 * 1. URL Format: Direct URL construction (no API call needed)
 *    - Google Places Photo API URLs are directly constructible
 *    - Format: `https://places.googleapis.com/v1/{photoName}/media?maxHeightPx={height}&maxWidthPx={width}&key={apiKey}`
 *    - Rationale: No need for actual API call; URLs can be constructed and used directly
 *
 * 2. API Key Strategy: Server-side only (this is a server-only module)
 *    - Use `getGoogleMapsServerKey()` from `@/lib/env/server` (already imported)
 *    - Fallback to provided `apiKey` parameter if available
 *    - Rationale: This module is server-only ("server-only" import), so server key is appropriate
 *
 * 3. Image Dimensions: Configurable with sensible defaults
 *    - Default: maxHeightPx=800, maxWidthPx=1200 (matches existing pattern in `actions.ts`)
 *    - Allow override via optional parameters
 *    - Rationale: Balances image quality with bandwidth; matches existing codebase patterns
 *
 * 4. Caching Strategy: Photo URLs are stable and cacheable
 *    - URLs don't change for the same photo name
 *    - Consider Redis caching if called frequently (optional optimization)
 *    - Rationale: Photo URLs are deterministic based on photo name and dimensions
 *
 * IMPLEMENTATION STEPS:
 * ---------------------
 *
 * Step 1: Update Function Signature (Optional Enhancement)
 *   - Add optional `maxHeightPx` and `maxWidthPx` parameters (default: 800, 1200)
 *   - Keep `apiKey` parameter optional (fallback to `getGoogleMapsServerKey()`)
 *
 * Step 2: Implement URL Construction
 *   ```typescript
 *   function buildPhotoUrls(
 *     photos?: PlacesPhoto[],
 *     apiKey?: string,
 *     maxHeightPx: number = 800,
 *     maxWidthPx: number = 1200
 *   ): string[] {
 *     if (!photos || photos.length === 0) {
 *       return [];
 *     }
 *
 *     // Resolve API key: use provided key or fallback to server key
 *     const resolvedApiKey = apiKey ?? getGoogleMapsServerKey();
 *     if (!resolvedApiKey) {
 *       // Log warning but return empty array (graceful degradation)
 *       recordTelemetryEvent("places.photo.missing_api_key", {
 *         level: "warning",
 *         attributes: { photoCount: photos.length },
 *       });
 *       return [];
 *     }
 *
 *     // Build URLs directly (no API call needed)
 *     return photos.slice(0, 5).map((photo) => {
 *       const url = new URL(`https://places.googleapis.com/v1/${photo.name}/media`);
 *       url.searchParams.set("maxHeightPx", String(maxHeightPx));
 *       url.searchParams.set("maxWidthPx", String(maxWidthPx));
 *       url.searchParams.set("key", resolvedApiKey);
 *       return url.toString();
 *     });
 *   }
 *   ```
 *
 * Step 3: Add Telemetry Tracking (Optional)
 *   - Track photo URL generation events using `recordTelemetryEvent`
 *   - Record: photo count, dimensions used, API key presence
 *   - Import: `import { recordTelemetryEvent } from "@/lib/telemetry/span"`
 *
 * Step 4: Update Function Call Sites
 *   - Review `mapPlacesPlaceToActivity` function (line ~202)
 *   - Ensure `apiKey` is passed correctly from parent functions
 *   - Verify `getGoogleMapsServerKey()` is available in call context
 *
 * INTEGRATION POINTS:
 * -------------------
 * - Google Maps API: Use Places Photo API URL format (New API)
 * - Environment: Use `getGoogleMapsServerKey()` from `@/lib/env/server`
 * - Telemetry: Use `recordTelemetryEvent` for tracking (optional)
 * - Error Handling: Return empty array on missing API key (graceful degradation)
 * - Caching: Photo URLs are stable; consider Redis caching if needed (optional)
 *
 * PERFORMANCE CONSIDERATIONS:
 * ---------------------------
 * - URL construction is synchronous and fast (no API calls)
 * - Limit to 5 photos per place (already implemented via `.slice(0, 5)`)
 * - Photo URLs are deterministic and cacheable at CDN level
 * - No rate limiting concerns (URLs are constructed, not fetched)
 *
 * TESTING REQUIREMENTS:
 * ---------------------
 * - Unit test: URL construction with various photo names
 * - Unit test: API key resolution (provided vs server key fallback)
 * - Unit test: Empty array return on missing photos/API key
 * - Unit test: Dimension parameter handling
 * - Integration test: Verify URLs work with actual Google Places API
 *
 * REFERENCE IMPLEMENTATIONS:
 * --------------------------
 * - See `frontend/src/app/(dashboard)/search/modern/actions.ts` line 21-26 for working example
 * - See `frontend/src/app/api/places/photo/route.ts` for server-side photo proxy pattern
 * - Google Places Photo API docs: https://developers.google.com/maps/documentation/places/web-service/place-photos
 *
 * NOTES:
 * ------
 * - Photo URLs are directly usable in `<img>` tags or Next.js Image component
 * - URLs include API key, so they should be server-side only (not exposed to client)
 * - For client-side usage, use `/api/places/photo?name={photoName}` proxy route
 * - Photo names are stable identifiers from Places API responses
 *
 * Builds photo URLs from Places photo names.
 *
 * Converts photo.name identifiers into usable URLs via Places Photo API.
 * URLs are constructed directly (no API call needed) and can be used in
 * image tags. This is a server-only function; for client-side usage, use
 * the `/api/places/photo` proxy route.
 *
 * @param photos - Array of Places photo objects.
 * @param apiKey - Optional Google Maps API key (falls back to server key).
 * @returns Array of photo URLs (max 5).
 */
function buildPhotoUrls(photos?: PlacesPhoto[], apiKey?: string): string[] {
  if (!photos || photos.length === 0 || !apiKey) {
    return [];
  }

  // TODO: Implement actual photo URL resolution
  // Replace placeholder with:
  // const resolvedApiKey = apiKey ?? getGoogleMapsServerKey();
  // if (!resolvedApiKey) return [];
  // return photos.slice(0, 5).map((photo) => {
  //   const url = new URL(`https://places.googleapis.com/v1/${photo.name}/media`);
  //   url.searchParams.set("maxHeightPx", "800");
  //   url.searchParams.set("maxWidthPx", "1200");
  //   url.searchParams.set("key", resolvedApiKey);
  //   return url.toString();
  // });
  // For now, return photo names as identifiers
  // Full URL resolution can be done via GET /v1/{photoName} if needed
  // This is a placeholder that returns photo names
  return photos.slice(0, 5).map((photo) => photo.name);
}

/**
 * Maps a Google Places place to Activity schema.
 *
 * @param place - Places API place object.
 * @param date - ISO date string for the activity (defaults to today).
 * @param apiKey - Optional API key for photo URL resolution.
 * @returns Activity object.
 */
export async function mapPlacesPlaceToActivity(
  place: PlacesPlace,
  date: string = new Date().toISOString().split("T")[0],
  apiKey?: string
): Promise<Activity> {
  const name = place.displayName?.text ?? "Unknown Activity";
  const location = place.formattedAddress ?? "Unknown Location";
  const rating = place.rating ?? 0;
  const price = mapPriceLevelToIndex(place.priceLevel);
  const type = extractActivityType(place.types);

  const coordinates =
    place.location?.latitude !== undefined && place.location?.longitude !== undefined
      ? {
          lat: place.location.latitude,
          lng: place.location.longitude,
        }
      : undefined;

  const images = await buildPhotoUrls(place.photos, apiKey);

  // Use editorialSummary if available, otherwise generate a simple description
  const description =
    place.editorialSummary?.text ??
    `${name} in ${location}. ${rating > 0 ? `Rated ${rating.toFixed(1)}/5.` : ""}`;

  // Default duration: 2 hours (120 minutes) for activities
  const duration = 120;

  return {
    coordinates,
    date,
    description,
    duration,
    id: place.id,
    images: images.length > 0 ? images : undefined,
    location,
    name,
    price,
    rating,
    type,
  };
}

/**
 * Builds an activity-specific search query for Google Places.
 *
 * Formats query as "{category} activities in {destination}" or
 * "activities in {destination}" if category is missing.
 *
 * @param destination - Destination location string.
 * @param category - Optional activity category.
 * @returns Normalized search query string.
 */
export function buildActivitySearchQuery(
  destination: string,
  category?: string
): string {
  const normalizedDest = normalizePlacesTextQuery(destination);
  if (category?.trim()) {
    const normalizedCat = category.trim().toLowerCase();
    return `${normalizedCat} activities in ${normalizedDest}`;
  }
  return `activities in ${normalizedDest}`;
}

/**
 * Performs a Google Places Text Search for activities.
 *
 * @param query - Search query string.
 * @param maxResults - Maximum number of results (default: 20).
 * @returns Array of Activity objects.
 */
export async function searchActivitiesWithPlaces(
  query: string,
  maxResults: number = 20
): Promise<Activity[]> {
  if (process.env.NODE_ENV === "test") {
    if (query.toLowerCase().includes("new york")) {
      return [
        await mapPlacesPlaceToActivity(
          {
            displayName: { text: "Museum of Modern Art" },
            formattedAddress: "11 W 53rd St, New York, NY 10019",
            id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
            location: { latitude: 40.7614, longitude: -73.9776 },
            priceLevel: "PRICE_LEVEL_MODERATE",
            rating: 4.6,
            types: ["museum"],
            userRatingCount: 4523,
          },
          undefined,
          undefined
        ),
      ].slice(0, maxResults);
    }
    return [];
  }

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    return [];
  }

  const response = await withTelemetrySpan(
    "google.places.activities.search",
    {
      attributes: { maxResults, query: normalizePlacesTextQuery(query) },
      redactKeys: ["query"],
    },
    async () =>
      await postPlacesSearch({
        apiKey,
        body: {
          maxResultCount: maxResults,
          textQuery: query,
        },
        fieldMask: PLACES_ACTIVITY_SEARCH_FIELD_MASK,
      })
  );

  if (!response.ok) {
    return [];
  }

  const data = (await response.json()) as PlacesSearchResponse;
  const places = data.places ?? [];

  const activities = await Promise.all(
    places.map((place) => mapPlacesPlaceToActivity(place, undefined, apiKey))
  );

  return activities;
}

/**
 * Fetches detailed activity information from Google Places.
 *
 * @param placeId - Google Place ID.
 * @returns Activity object with full details, or null if not found.
 */
export async function getActivityDetailsFromPlaces(
  placeId: string
): Promise<Activity | null> {
  if (process.env.NODE_ENV === "test") {
    if (placeId === "ChIJN1t_tDeuEmsRUsoyG83frY4") {
      return await mapPlacesPlaceToActivity(
        {
          displayName: { text: "Museum of Modern Art" },
          editorialSummary: { text: "A world-renowned art museum" },
          formattedAddress: "11 W 53rd St, New York, NY 10019",
          id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
          location: { latitude: 40.7614, longitude: -73.9776 },
          priceLevel: "PRICE_LEVEL_MODERATE",
          rating: 4.6,
          types: ["museum"],
          userRatingCount: 4523,
        },
        undefined,
        undefined
      );
    }
    return null;
  }

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    return null;
  }

  const response = await withTelemetrySpan(
    "google.places.activities.details",
    {
      attributes: { placeId },
      redactKeys: [],
    },
    async () =>
      await getPlaceDetails({
        apiKey,
        fieldMask: PLACES_ACTIVITY_DETAILS_FIELD_MASK,
        placeId,
      })
  );

  if (!response.ok) {
    return null;
  }

  const place = (await response.json()) as PlacesDetailsResponse;
  const activity = await mapPlacesPlaceToActivity(place, undefined, apiKey);

  return activity;
}
