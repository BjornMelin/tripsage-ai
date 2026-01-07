/**
 * @fileoverview Canonical server-only Places service with short TTL caching and SSRF-safe provider calls.
 */

import "server-only";

import type { UpstreamPlace } from "@schemas/api";
import { upstreamPlaceSchema, upstreamPlacesSearchResponseSchema } from "@schemas/api";
import type {
  PlaceDetails,
  PlaceDetailsParams,
  PlaceSummary,
  SearchPlacesParams,
  SearchPlacesResult,
} from "@schemas/places";
import {
  placeDetailsParamsSchema,
  placeDetailsSchema,
  placeSummarySchema,
  searchPlacesParamsSchema,
  searchPlacesResultSchema,
} from "@schemas/places";
import { hashInputForCache } from "@/lib/cache/hash";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getCachedJsonSafe, setCachedJson } from "@/lib/cache/upstash";
import { getPlaceDetails, postPlacesSearch } from "@/lib/google/client";
import { normalizePlacesTextQuery } from "@/lib/google/places-utils";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Default TTL for caching places search results (10 minutes). */
const PLACES_SEARCH_CACHE_TTL_SECONDS = 10 * 60;

/** Field mask for Places Text Search: only fields needed for UI + tools. */
const PLACES_SEARCH_FIELD_MASK =
  "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types";

/** Field mask for Places Details: full details surface (do not cache payload). */
const PLACES_DETAILS_FIELD_MASK =
  "id,displayName,formattedAddress,location,url,googleMapsUri,internationalPhoneNumber,rating,userRatingCount,regularOpeningHours,photos.name,businessStatus,types,editorialSummary,websiteUri";

export type PlacesServiceErrorCode =
  | "invalid_request"
  | "not_found"
  | "rate_limited"
  | "external_api_error"
  | "upstream_parse_error"
  | "upstream_validation_error";

export class PlacesServiceError extends Error {
  public readonly code: PlacesServiceErrorCode;
  public readonly status: number;

  constructor(
    code: PlacesServiceErrorCode,
    status: number,
    message: string,
    options?: { cause?: unknown }
  ) {
    super(message);
    this.name = "PlacesServiceError";
    this.code = code;
    this.status = status;
    if (options?.cause) {
      this.cause = options.cause;
    }
  }
}

function buildMapsUrl(placeId: string): string {
  // Safe, provider-owned URL. Do not accept user-controlled URLs.
  const encoded = encodeURIComponent(placeId);
  return `https://www.google.com/maps/place/?q=place_id:${encoded}`;
}

function normalizePlaceIdForGoogle(placeId: string): string {
  return placeId.startsWith("places/") ? placeId : `places/${placeId}`;
}

function mapUpstreamPlaceToSummary(place: UpstreamPlace): PlaceSummary {
  const coordinates =
    place.location?.latitude !== undefined && place.location?.longitude !== undefined
      ? { lat: place.location.latitude, lng: place.location.longitude }
      : undefined;

  const mapped = {
    coordinates,
    formattedAddress: place.formattedAddress,
    name: place.displayName?.text ?? place.formattedAddress ?? "Unnamed place",
    photoName: place.photos?.[0]?.name,
    placeId: place.id,
    rating: place.rating,
    types: place.types ?? [],
    url: place.googleMapsUri ?? place.url ?? buildMapsUrl(place.id),
    userRatingCount: place.userRatingCount,
  } satisfies PlaceSummary;

  return placeSummarySchema.parse(mapped);
}

function mapUpstreamPlaceToDetails(place: UpstreamPlace): PlaceDetails {
  const base = mapUpstreamPlaceToSummary(place);

  const openNowValue = (place.regularOpeningHours as { openNow?: unknown } | undefined)
    ?.openNow;
  const openNow = typeof openNowValue === "boolean" ? openNowValue : undefined;

  const mapped = {
    ...base,
    businessStatus: place.businessStatus,
    editorialSummary: place.editorialSummary?.text,
    internationalPhoneNumber: place.internationalPhoneNumber,
    regularOpeningHours: place.regularOpeningHours
      ? {
          openNow,
          weekdayDescriptions: place.regularOpeningHours.weekdayDescriptions,
        }
      : undefined,
    websiteUri: place.websiteUri,
  } satisfies PlaceDetails;

  return placeDetailsSchema.parse(mapped);
}

function filterByIncludedTypes(
  places: PlaceSummary[],
  includedTypes?: string[]
): PlaceSummary[] {
  if (!includedTypes || includedTypes.length === 0) return places;
  const allowed = new Set(includedTypes.map((t) => t.toLowerCase()));
  return places.filter((place) =>
    place.types.some((type) => allowed.has(type.toLowerCase()))
  );
}

function buildSearchCacheKey(params: SearchPlacesParams): string {
  // Never store raw query strings in Redis keys.
  const normalizedQuery = normalizePlacesTextQuery(params.query);
  const canonical = canonicalizeParamsForCache({
    includedTypes: params.filters?.includedTypes ?? null,
    locationBias: params.locationBias
      ? `${params.locationBias.lat},${params.locationBias.lon},${params.locationBias.radiusMeters}`
      : null,
    maxResults: params.maxResults,
    query: normalizedQuery,
  });
  const hash = hashInputForCache(canonical);
  return `places:search:v1:${hash}`;
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new PlacesServiceError(
      "upstream_parse_error",
      502,
      "Invalid JSON from Places API"
    );
  }
}

export type PlacesService = {
  searchPlaces: (params: SearchPlacesParams) => Promise<SearchPlacesResult>;
  getPlaceDetails: (params: PlaceDetailsParams) => Promise<PlaceDetails>;
};

export type PlacesServiceDeps = {
  apiKey: string;
  cacheTtlSeconds?: number;
};

function clampSearchTtlSeconds(ttlSeconds: number): number {
  // SPEC-0106: short TTL (5–15 minutes).
  const Min = 5 * 60;
  const Max = 15 * 60;
  if (!Number.isFinite(ttlSeconds)) return PLACES_SEARCH_CACHE_TTL_SECONDS;
  return Math.min(Math.max(Math.trunc(ttlSeconds), Min), Max);
}

export function createPlacesService(deps: PlacesServiceDeps): PlacesService {
  const effectiveSearchTtlSeconds = clampSearchTtlSeconds(
    deps.cacheTtlSeconds ?? PLACES_SEARCH_CACHE_TTL_SECONDS
  );

  return {
    getPlaceDetails: async (rawParams) =>
      await withTelemetrySpan(
        "places.service.details",
        {
          attributes: {
            hasSessionToken: Boolean(rawParams.sessionToken),
          },
        },
        async () => {
          const validated = placeDetailsParamsSchema.parse(rawParams);
          const normalizedId = normalizePlaceIdForGoogle(validated.placeId);

          const response = await getPlaceDetails({
            apiKey: deps.apiKey,
            fieldMask: PLACES_DETAILS_FIELD_MASK,
            placeId: normalizedId,
            sessionToken: validated.sessionToken,
          });

          if (!response.ok) {
            if (response.status === 404) {
              throw new PlacesServiceError("not_found", 404, "Place not found");
            }
            if (response.status === 429) {
              throw new PlacesServiceError(
                "rate_limited",
                429,
                "Upstream rate limit exceeded"
              );
            }
            const status =
              response.status >= 400 && response.status < 500 ? response.status : 502;
            throw new PlacesServiceError(
              "external_api_error",
              status,
              "External places service error"
            );
          }

          const rawData = await parseJsonResponse(response);
          const parsed = upstreamPlaceSchema.safeParse(rawData);
          if (!parsed.success) {
            throw new PlacesServiceError(
              "upstream_validation_error",
              502,
              "Invalid response from Places API",
              { cause: parsed.error }
            );
          }

          return mapUpstreamPlaceToDetails(parsed.data);
        }
      ),
    searchPlaces: async (rawParams) =>
      await withTelemetrySpan(
        "places.service.search",
        {
          attributes: {
            maxResults: rawParams.maxResults ?? null,
          },
          redactKeys: ["query"],
        },
        async () => {
          const validated = searchPlacesParamsSchema.parse(rawParams);
          const cacheKey = buildSearchCacheKey(validated);

          const cached = await getCachedJsonSafe(cacheKey, searchPlacesResultSchema, {
            namespace: "places",
          });
          if (cached.status === "hit") {
            return cached.data;
          }

          const requestBody: Record<string, unknown> = {
            maxResultCount: validated.maxResults,
            textQuery: validated.query,
          };

          if (validated.locationBias) {
            requestBody.locationBias = {
              circle: {
                center: {
                  latitude: validated.locationBias.lat,
                  longitude: validated.locationBias.lon,
                },
                radius: validated.locationBias.radiusMeters,
              },
            };
          }

          const response = await postPlacesSearch({
            apiKey: deps.apiKey,
            body: requestBody,
            fieldMask: PLACES_SEARCH_FIELD_MASK,
          });

          if (!response.ok) {
            if (response.status === 429) {
              throw new PlacesServiceError(
                "rate_limited",
                429,
                "Upstream rate limit exceeded"
              );
            }
            throw new PlacesServiceError(
              "external_api_error",
              502,
              "External places service error"
            );
          }

          const rawData = await parseJsonResponse(response);
          const parsed = upstreamPlacesSearchResponseSchema.safeParse(rawData);
          if (!parsed.success) {
            throw new PlacesServiceError(
              "upstream_validation_error",
              502,
              "Invalid response from Places API",
              { cause: parsed.error }
            );
          }

          const places = filterByIncludedTypes(
            parsed.data.places.map(mapUpstreamPlaceToSummary),
            validated.filters?.includedTypes
          );

          const result: SearchPlacesResult = searchPlacesResultSchema.parse({
            places,
          });

          await setCachedJson(cacheKey, result, effectiveSearchTtlSeconds, {
            namespace: "places",
          });

          return result;
        }
      ),
  };
}
