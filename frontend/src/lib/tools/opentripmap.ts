/**
 * @fileoverview OpenTripMap POI lookup tool.
 *
 * Provides point-of-interest lookup using OpenTripMap API with caching
 * and rate limiting. Uses Google Maps Geocoding API for destination-based
 * lookups. Falls back to stub if API keys are not configured.
 */

import { tool } from "ai";
import { z } from "zod";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Transform raw API response (snake_case) to normalized structure (camelCase).
 *
 * External API returns snake_case fields which we transform immediately to
 * camelCase for internal use per Google TS style guide.
 *
 * @param rawApiResponse Raw API response with snake_case fields.
 * @returns Normalized POI array.
 */
function transformApiResponse(rawApiResponse: unknown): NormalizedPoi[] {
  // Type assertion for external API response - API uses snake_case
  // We access fields using bracket notation to avoid naming convention issues
  const apiData = rawApiResponse as {
    features?: Array<{
      geometry?: {
        coordinates?: [number, number];
      };
      properties?: Record<string, unknown>;
    }>;
  };

  const pois: NormalizedPoi[] = [];

  for (const feature of apiData.features ?? []) {
    const props = feature.properties;
    const coords = feature.geometry?.coordinates;
    if (!coords || coords.length < 2 || !props) continue;

    // Access snake_case fields from external API
    // External API uses snake_case - use type assertion to access safely
    const propsRecord = props as Record<string, unknown> & {
      // biome-ignore lint/style/useNamingConvention: External API field name
      wikipedia_extracts?: { text?: string };
    };
    const wikipediaExtractsRaw = propsRecord.wikipedia_extracts;
    const poi: NormalizedPoi = {
      description: wikipediaExtractsRaw?.text,
      distance: propsRecord.dist as number | undefined,
      image: propsRecord.image as string | undefined,
      kind: propsRecord.kind as string | undefined,
      lat: coords[1],
      lon: coords[0],
      name: (propsRecord.name as string | undefined) ?? "Unnamed POI",
      xid: propsRecord.xid as string | undefined,
    };

    if (poi.xid) {
      poi.url = `https://opentripmap.io/en/card/${poi.xid}`;
    }

    pois.push(poi);
  }

  return pois;
}

/**
 * Normalized POI result structure.
 */
type NormalizedPoi = {
  name: string;
  xid?: string;
  lat: number;
  lon: number;
  kind?: string;
  distance?: number;
  description?: string;
  image?: string;
  url?: string;
};

/**
 * Geocode a destination name to coordinates using Google Maps Geocoding API.
 *
 * Uses Google Maps Geocoding API to convert destination strings to coordinates.
 * Returns null if geocoding fails or API key is not configured.
 *
 * @param destination Destination name to geocode.
 * @returns Promise resolving to coordinates or null.
 */
async function geocodeDestinationWithGoogleMaps(
  destination: string
): Promise<{ lat: number; lon: number } | null> {
  const googleMapsApiKey =
    typeof process !== "undefined" && process.env && process.env.GOOGLE_MAPS_API_KEY
      ? process.env.GOOGLE_MAPS_API_KEY
      : undefined;

  if (!googleMapsApiKey || googleMapsApiKey === "undefined") {
    return null;
  }

  try {
    const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
    url.searchParams.set("address", destination);
    url.searchParams.set("key", googleMapsApiKey);

    const res = await fetch(url);
    if (!res.ok) {
      return null;
    }

    const data = (await res.json()) as {
      status?: string;
      results?: Array<{
        geometry?: {
          location?: { lat?: number; lng?: number };
        };
      }>;
    };

    if (data.status !== "OK" || !data.results || data.results.length === 0) {
      return null;
    }

    const firstResult = data.results[0];
    const location = firstResult.geometry?.location;
    if (
      location &&
      typeof location.lat === "number" &&
      typeof location.lng === "number"
    ) {
      return { lat: location.lat, lon: location.lng };
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Fetch POIs from OpenTripMap API.
 *
 * @param lat Latitude coordinate.
 * @param lon Longitude coordinate.
 * @param radiusMeters Search radius in meters.
 * @param apiKey OpenTripMap API key.
 * @returns Promise resolving to normalized POI array.
 */
async function fetchPoisFromApi(
  lat: number,
  lon: number,
  radiusMeters: number,
  apiKey: string
): Promise<NormalizedPoi[]> {
  // API expects radius in meters – pass through without conversion
  const url = `https://api.opentripmap.io/0.1/en/places/radius?radius=${radiusMeters}&lon=${lon}&lat=${lat}&limit=20&apikey=${apiKey}`;

  const response = await fetch(url, {
    headers: {
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`OpenTripMap API error: ${response.status}`);
  }

  const rawData = await response.json();
  return transformApiResponse(rawData);
}

/**
 * Zod input schema for lookup POI context tool.
 *
 * Exported for use in guardrails validation and cache key generation.
 */
export const lookupPoiInputSchema = z
  .object({
    destination: z.string().optional(),
    lat: z.number().optional(),
    lon: z.number().optional(),
    radiusMeters: z.number().int().positive().default(1000),
  })
  .refine(
    (o) =>
      Boolean(o.destination) ||
      (typeof o.lat === "number" && typeof o.lon === "number"),
    { message: "Provide destination or lat/lon" }
  );

export const lookupPoiContext = tool({
  description:
    "Lookup points of interest near a destination or coordinate using OpenTripMap.",
  execute: async (params) => {
    // Validate input at boundary (AI SDK validates, but ensure for direct calls)
    const validatedParams = lookupPoiInputSchema.parse(params);
    return await withTelemetrySpan(
      "tool.opentripmap.lookup",
      {
        attributes: {
          hasCoordinates: Boolean(params.lat && params.lon),
          hasDestination: Boolean(params.destination),
          "tool.name": "lookupPoiContext",
        },
      },
      async () => {
        // Check for API key - handle both Node.js and test environments
        const apiKey =
          typeof process !== "undefined" &&
          process.env &&
          process.env.OPENTRIPMAP_API_KEY
            ? process.env.OPENTRIPMAP_API_KEY
            : undefined;
        if (!apiKey || apiKey === "undefined") {
          // Fallback to stub if API key not configured
          return {
            inputs: validatedParams,
            pois: [],
            provider: "stub",
          } as const;
        }

        let lat: number;
        let lon: number;

        if (validatedParams.lat && validatedParams.lon) {
          lat = validatedParams.lat;
          lon = validatedParams.lon;
        } else if (validatedParams.destination) {
          // Normalize destination for cache key (Google Maps geocoding)
          const normalizedDestination = validatedParams.destination
            .toLowerCase()
            .trim();
          const googleMapsGeocodeCacheKey = `opentripmap:geocode:googlemaps:${normalizedDestination}`;

          // Check cache for Google Maps geocoding result
          let coords = await getCachedJson<{ lat: number; lon: number }>(
            googleMapsGeocodeCacheKey
          );

          // If not cached, geocode with Google Maps and cache the result
          if (!coords) {
            coords = await geocodeDestinationWithGoogleMaps(
              validatedParams.destination
            );
            if (coords) {
              // Cache Google Maps geocoding result (24h = 86400 seconds)
              await setCachedJson(googleMapsGeocodeCacheKey, coords, 86400);
            }
          }

          if (!coords) {
            return {
              error: "Geocoding not available",
              inputs: validatedParams,
              pois: [],
              provider: "opentripmap",
            } as const;
          }
          lat = coords.lat;
          lon = coords.lon;
        } else {
          // Should not reach here due to Zod validation, but handle defensively
          throw new Error("Missing coordinates or destination");
        }

        const radiusMeters = validatedParams.radiusMeters ?? 1000;
        const cacheKey = `opentripmap:${lat}:${lon}:${radiusMeters}`;

        // Check cache (24h TTL)
        const cached = await getCachedJson<NormalizedPoi[]>(cacheKey);
        if (cached) {
          return {
            fromCache: true,
            inputs: validatedParams,
            pois: cached,
            provider: "opentripmap",
          } as const;
        }

        // Fetch from API
        const pois = await fetchPoisFromApi(lat, lon, radiusMeters, apiKey);

        // Cache results (24h = 86400 seconds)
        await setCachedJson(cacheKey, pois, 86400);

        return {
          fromCache: false,
          inputs: validatedParams,
          pois,
          provider: "opentripmap",
        } as const;
      }
    );
  },
  inputSchema: lookupPoiInputSchema,
});
