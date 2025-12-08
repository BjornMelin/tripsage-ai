/**
 * @fileoverview Google Places nearby landmarks service for hotel location context.
 *
 * Fetches notable places near a hotel (tourist attractions, restaurants, transit)
 * to provide location context and walkability information.
 */

import "server-only";

import { getGoogleMapsServerKey } from "@/lib/env/server";
import { postNearbySearch } from "@/lib/google/client";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Field mask for nearby landmark search (minimal useful fields).
 */
const NEARBY_LANDMARKS_FIELD_MASK =
  "places.id,places.displayName,places.shortFormattedAddress,places.types,places.rating";

const MUSEUM_TYPES = [
  "museum",
  "art_gallery",
  "aquarium",
  "history_museum",
  "science_museum",
];

/**
 * Place types for tourist/landmark searches.
 */
const LANDMARK_PLACE_TYPES = [
  "tourist_attraction",
  "museum",
  "landmark",
  "national_park",
  "art_gallery",
  "zoo",
  "aquarium",
  "amusement_park",
];

/**
 * Place types for transit searches.
 */
const TRANSIT_PLACE_TYPES = [
  "subway_station",
  "train_station",
  "bus_station",
  "light_rail_station",
];

/**
 * Place types for dining searches.
 */
const DINING_PLACE_TYPES = ["restaurant", "cafe", "bar"];
const TRANSIT_RADIUS_MULTIPLIER = 0.5;

const placesLogger = createServerLogger("google.places.landmarks");

type UpstreamPlace = {
  displayName?: { text?: string };
  id?: string;
  rating?: number;
  shortFormattedAddress?: string;
  types?: string[];
  location?: { latitude?: number; longitude?: number };
};

/** Landmark result from nearby search */
export interface NearbyLandmark {
  /** Short address (e.g., "1600 Pennsylvania Ave NW") */
  address?: string;
  /** Display name of the place */
  name: string;
  /** Google Places ID */
  placeId: string;
  /** User rating (1-5) */
  rating?: number;
  /** Primary type (e.g., "museum", "restaurant") */
  type: string;
}

/** Result of nearby landmarks search */
export interface NearbyLandmarksResult {
  /** Notable dining options */
  dining: NearbyLandmark[];
  /** Tourist attractions and landmarks */
  landmarks: NearbyLandmark[];
  /** Nearby transit options */
  transit: NearbyLandmark[];
}

/**
 * Maps Google Places response to NearbyLandmark array.
 */
function mapPlacesToLandmarks(places: UpstreamPlace[]): NearbyLandmark[] {
  return places
    .filter((place) => place.id && place.displayName?.text)
    .map((place) => {
      const primaryType =
        typeof place.types?.[0] === "string" ? place.types[0] : undefined;
      const normalizedType = primaryType?.replace(/_/g, " ") ?? "place";
      return {
        address: place.shortFormattedAddress ?? "",
        name: place.displayName?.text ?? "",
        placeId: place.id ?? "",
        rating: place.rating,
        type: normalizedType,
      };
    });
}

/**
 * Search for nearby places of specific types.
 *
 * @param lat - Latitude of the search center
 * @param lng - Longitude of the search center
 * @param types - Place types to search for
 * @param radiusMeters - Search radius in meters
 * @param maxResults - Maximum results to return
 * @returns Array of nearby landmarks
 */
async function searchNearbyPlaces(
  lat: number,
  lng: number,
  types: string[],
  radiusMeters: number,
  maxResults: number
): Promise<NearbyLandmark[]> {
  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch (error) {
    placesLogger.error("failed_to_retrieve_google_maps_key", {
      error: error instanceof Error ? error.message : String(error),
    });
    return [];
  }

  const response = await postNearbySearch({
    apiKey,
    fieldMask: NEARBY_LANDMARKS_FIELD_MASK,
    includedTypes: types,
    lat,
    lng,
    maxResultCount: maxResults,
    radiusMeters,
  });

  if (!response.ok) {
    placesLogger.warn("places_nearby_non_ok_response", {
      status: response.status,
      statusText: response.statusText,
    });
    return [];
  }

  let data: { places?: unknown[] };
  try {
    data = await response.json();
  } catch (error) {
    placesLogger.error("places_nearby_parse_failed", {
      error: error instanceof Error ? error.message : String(error),
    });
    return [];
  }

  const places: UpstreamPlace[] = Array.isArray(data.places)
    ? (data.places as UpstreamPlace[])
    : [];

  return mapPlacesToLandmarks(places);
}

/**
 * Fetches nearby landmarks, transit, and dining options for a hotel location.
 *
 * Uses Google Places Nearby Search to find notable places within walking
 * distance of the hotel. Results are categorized by type.
 *
 * @param lat - Hotel latitude
 * @param lng - Hotel longitude
 * @param radiusMeters - Search radius in meters (default 1000m = ~12 min walk)
 * @returns Object with landmarks, transit, and dining arrays
 */
export async function getNearbyLandmarks(
  lat: number,
  lng: number,
  radiusMeters = 1000
): Promise<NearbyLandmarksResult> {
  return await withTelemetrySpan(
    "google.places.nearby.landmarks",
    {
      attributes: { lat, lng, radiusMeters },
      redactKeys: [],
    },
    async () => {
      // Run all three searches in parallel
      const [landmarks, transit, dining] = await Promise.all([
        searchNearbyPlaces(lat, lng, LANDMARK_PLACE_TYPES, radiusMeters, 5),
        searchNearbyPlaces(
          lat,
          lng,
          TRANSIT_PLACE_TYPES,
          radiusMeters * TRANSIT_RADIUS_MULTIPLIER,
          3
        ),
        searchNearbyPlaces(lat, lng, DINING_PLACE_TYPES, radiusMeters, 5),
      ]);

      return { dining, landmarks, transit };
    }
  );
}

/**
 * Formats nearby landmarks into human-readable location highlights.
 *
 * Creates short descriptions like "Near Times Square" or "5 min to subway".
 *
 * @param landmarks - NearbyLandmarksResult from getNearbyLandmarks
 * @returns Array of location highlight strings (max 4)
 */
export function formatLandmarksAsHighlights(
  landmarks: NearbyLandmarksResult
): string[] {
  const highlights: string[] = [];

  // Add top landmark if available
  const topLandmark = landmarks.landmarks[0];
  if (topLandmark) {
    highlights.push(`Near ${topLandmark.name}`);
  }

  // Add transit info if available
  const transit = landmarks.transit[0];
  if (transit) {
    highlights.push(`${transit.name} nearby`);
  }

  // Add dining info if multiple options
  if (landmarks.dining.length >= 3) {
    highlights.push("Many dining options");
  }

  // Add museum/attraction count if multiple
  const museums = landmarks.landmarks.filter((l) =>
    MUSEUM_TYPES.some((type) => {
      const normalized = type.replace(/_/g, " ");
      return l.type === normalized;
    })
  );
  if (museums.length >= 2) {
    highlights.push(`${museums.length} museums nearby`);
  }

  return highlights.slice(0, 4);
}
