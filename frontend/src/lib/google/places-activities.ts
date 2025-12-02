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

/** Maximum number of photos to include per activity. */
const MAX_ACTIVITY_PHOTOS = 5;

/** Default photo dimensions for activity images. */
const DEFAULT_PHOTO_DIMENSIONS = {
  maxHeightPx: 800,
  maxWidthPx: 1200,
} as const;

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
 * Builds client-safe photo URLs via the server-side photo proxy.
 *
 * Limits results to MAX_ACTIVITY_PHOTOS (5) to balance visual richness
 * with payload size and rendering performance. The photo proxy route
 * handles API key authentication internally.
 * 
 * @param photos - Array of PlacesPhoto objects.
 * @returns Array of client-safe photo URLs.
 */
function buildPhotoUrls(photos?: PlacesPhoto[]): string[] {
  if (!photos || photos.length === 0) {
    return [];
  }

  // Limit to MAX_ACTIVITY_PHOTOS to balance richness with performance
  return photos.slice(0, MAX_ACTIVITY_PHOTOS).map((photo) => {
    const params = new URLSearchParams({
      maxHeightPx: String(DEFAULT_PHOTO_DIMENSIONS.maxHeightPx),
      maxWidthPx: String(DEFAULT_PHOTO_DIMENSIONS.maxWidthPx),
      name: photo.name,
    });
    return `/api/places/photo?${params.toString()}`;
  });
}

/**
 * Maps a Google Places place to Activity schema.
 *
 * @param place - Places API place object.
 * @param date - ISO date string for the activity (defaults to today).
 * @returns Activity object.
 */
export function mapPlacesPlaceToActivity(
  place: PlacesPlace,
  date: string = new Date().toISOString().split("T")[0]
): Activity {
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

  const images = buildPhotoUrls(place.photos);

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

  const activities = places.map((place) => mapPlacesPlaceToActivity(place));

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
  const activity = mapPlacesPlaceToActivity(place);

  return activity;
}
