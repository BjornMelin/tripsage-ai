/**
 * @fileoverview Places search and details tools backed by the canonical Places service.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  createToolError,
  isToolError,
  TOOL_ERROR_CODES,
} from "@ai/tools/server/errors";
import type {
  PlaceDetails,
  PlaceDetailsParams,
  SearchPlacesParams,
  SearchPlacesResult,
} from "@schemas/places";
import {
  placeDetailsToolInputSchema,
  placeDetailsToolOutputSchema,
  searchPlacesToolInputSchema,
  searchPlacesToolOutputSchema,
} from "@schemas/places";
import {
  createPlacesService,
  type PlacesService,
  PlacesServiceError,
} from "@/features/search/server/places/places-service";
import { hashInputForCache } from "@/lib/cache/hash";
import { getGoogleMapsServerKey } from "@/lib/env/server";

type SearchPlacesInput = SearchPlacesParams;
type SearchPlacesOutput = SearchPlacesResult;

type PlaceDetailsInput = PlaceDetailsParams;
type PlaceDetailsOutput = PlaceDetails;

function getPlacesKeyOrThrow(): string {
  try {
    return getGoogleMapsServerKey();
  } catch {
    throw createToolError(
      TOOL_ERROR_CODES.placesNotConfigured,
      "Google Places API key is not configured",
      { provider: "googleplaces" }
    );
  }
}

function toProviderErrorMeta(message: string): Record<string, unknown> {
  return {
    messageHash: hashInputForCache(message),
    messageLength: message.length,
    provider: "googleplaces",
  };
}

function mapPlacesServiceErrorToToolError(
  err: PlacesServiceError,
  kind: "search" | "details"
): never {
  if (err.code === "invalid_request") {
    throw createToolError(TOOL_ERROR_CODES.invalidParams, err.message, {
      ...toProviderErrorMeta(err.message),
      kind,
      status: err.status,
    });
  }

  if (err.code === "rate_limited") {
    throw createToolError(TOOL_ERROR_CODES.toolRateLimited, err.message, {
      ...toProviderErrorMeta(err.message),
      kind,
      status: err.status,
    });
  }

  if (kind === "details" && err.code === "not_found") {
    throw createToolError(TOOL_ERROR_CODES.placesDetailsNotFound, err.message, {
      ...toProviderErrorMeta(err.message),
      kind,
      status: err.status,
    });
  }

  const code =
    kind === "search"
      ? TOOL_ERROR_CODES.placesSearchFailed
      : TOOL_ERROR_CODES.placesDetailsFailed;

  throw createToolError(code, err.message, {
    ...toProviderErrorMeta(err.message),
    kind,
    status: err.status,
  });
}

export const searchPlaces = createAiTool<SearchPlacesInput, SearchPlacesOutput>({
  description:
    "Search for places (POIs, restaurants, hotels). Returns canonical PlaceSummary results.",
  execute: async (params) => {
    try {
      const apiKey = getPlacesKeyOrThrow();
      const service: PlacesService = createPlacesService({ apiKey });
      return await service.searchPlaces(params);
    } catch (err) {
      if (isToolError(err)) {
        throw err;
      }
      if (err instanceof PlacesServiceError) {
        mapPlacesServiceErrorToToolError(err, "search");
        // Unreachable: mapPlacesServiceErrorToToolError always throws.
      }
      const message = err instanceof Error ? err.message : "unknown_error";
      throw createToolError(TOOL_ERROR_CODES.placesSearchFailed, message, {
        ...toProviderErrorMeta(message),
        kind: "search",
      });
    }
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 30,
      prefix: "ratelimit:agent:places:search",
      window: "1 m",
    },
    telemetry: {
      attributes: (params) => ({
        hasLocationBias: Boolean(params.locationBias),
        hasTypeFilters: Boolean(params.filters?.includedTypes?.length),
        maxResults: params.maxResults,
        provider: "googleplaces",
      }),
      redactKeys: ["query"],
    },
  },
  inputSchema: searchPlacesToolInputSchema,
  name: "search.places",
  outputSchema: searchPlacesToolOutputSchema,
  toModelOutput: (result) => ({
    placeCount: result.places.length,
    places: result.places.slice(0, 10).map((place) => ({
      formattedAddress: place.formattedAddress,
      name: place.name,
      placeId: place.placeId,
      rating: place.rating,
      types: place.types.slice(0, 4),
    })),
  }),
  validateOutput: true,
});

export const placeDetails = createAiTool<PlaceDetailsInput, PlaceDetailsOutput>({
  description: "Get place details by placeId. Returns canonical PlaceDetails.",
  execute: async (params) => {
    try {
      const apiKey = getPlacesKeyOrThrow();
      const service: PlacesService = createPlacesService({ apiKey });
      return await service.getPlaceDetails(params);
    } catch (err) {
      if (isToolError(err)) {
        throw err;
      }
      if (err instanceof PlacesServiceError) {
        mapPlacesServiceErrorToToolError(err, "details");
        // Unreachable: mapPlacesServiceErrorToToolError always throws.
      }
      const message = err instanceof Error ? err.message : "unknown_error";
      throw createToolError(TOOL_ERROR_CODES.placesDetailsFailed, message, {
        ...toProviderErrorMeta(message),
        kind: "details",
      });
    }
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 60,
      prefix: "ratelimit:agent:places:details",
      window: "1 m",
    },
    telemetry: {
      attributes: (params) => ({
        hasSessionToken: Boolean(params.sessionToken),
        provider: "googleplaces",
      }),
    },
  },
  inputSchema: placeDetailsToolInputSchema,
  name: "search.placeDetails",
  outputSchema: placeDetailsToolOutputSchema,
  toModelOutput: (result) => ({
    businessStatus: result.businessStatus,
    formattedAddress: result.formattedAddress,
    name: result.name,
    placeId: result.placeId,
    rating: result.rating,
    types: result.types.slice(0, 4),
    url: result.url,
    websiteUri: result.websiteUri,
  }),
  validateOutput: true,
});
