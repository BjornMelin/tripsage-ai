/**
 * @fileoverview Cache Components wrappers for Google Maps API requests.
 */

import "server-only";

import {
  type ComputeRoutesRequest,
  type RouteMatrixRequest,
  type TimezoneRequest,
  upstreamRouteMatrixResponseSchema,
  upstreamRoutesResponseSchema,
  upstreamTimezoneResponseSchema,
} from "@schemas/api";
import { cacheLife, cacheTag } from "next/cache";
import type { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import {
  getTimezone,
  parseNdjsonResponse,
  postComputeRouteMatrix,
  postComputeRoutes,
} from "@/lib/google/client";

type TimezoneResponse = z.output<typeof upstreamTimezoneResponseSchema>;
type ComputeRoutesResponse = z.output<typeof upstreamRoutesResponseSchema>;
type RouteMatrixResponse = z.output<typeof upstreamRouteMatrixResponseSchema>;

/**
 * Successful cached response wrapping data of type T.
 */
export type CachedOk<T> = { ok: true; data: T };

/**
 * Error response from a cached Google API request.
 */
export type CachedErr = {
  details?: string;
  ok: false;
  error: string;
  reason: string;
  status: number;
  upstreamStatus?: number;
};

/**
 * Result of a cached Google API request, either success or error.
 */
export type CachedResult<T> = CachedOk<T> | CachedErr;

type CacheDurations = {
  expire: number;
  revalidate: number;
  stale: number;
};

function tryApplyCacheDirectives(tags: string[], durations: CacheDurations): void {
  try {
    cacheTag(...tags);
    cacheLife(durations);
  } catch {
    // Ignore Cache Components directives when executed outside the Next runtime (e.g. unit tests).
  }
}

/**
 * Fetches and validates Google Time Zone API responses with Cache Components.
 *
 * Note: We intentionally cache short-lived upstream failures to reduce stampedes.
 *
 * @param input - Timezone lookup payload containing latitude, longitude, and POSIX timestamp.
 * @returns Promise resolving to a CachedResult containing the validated TimezoneResponse or error details.
 */
export async function getTimezoneCached(input: {
  lat: TimezoneRequest["lat"];
  lng: TimezoneRequest["lng"];
  timestamp: TimezoneRequest["timestamp"];
}): Promise<CachedResult<TimezoneResponse>> {
  "use cache";

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    tryApplyCacheDirectives(["google-timezone"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "google_maps_not_configured",
      ok: false,
      reason: "Google Maps API key is not configured",
      status: 500,
    };
  }

  let response: Response;
  try {
    response = await getTimezone({
      apiKey,
      lat: input.lat,
      lng: input.lng,
      timestamp: input.timestamp,
    });
  } catch {
    tryApplyCacheDirectives(["google-timezone"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "external_api_error",
      ok: false,
      reason: "Failed to fetch timezone data",
      status: 502,
    };
  }

  if (!response.ok) {
    const details = response.status < 500 ? await response.text() : "";
    tryApplyCacheDirectives(["google-timezone"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      details: details.slice(0, 500),
      error: "upstream_error",
      ok: false,
      reason: `Time Zone API returned ${response.status}`,
      status: response.status >= 400 && response.status < 500 ? response.status : 502,
      upstreamStatus: response.status,
    };
  }

  let rawData: unknown;
  try {
    rawData = await response.json();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    tryApplyCacheDirectives(["google-timezone"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "upstream_parse_error",
      ok: false,
      reason: `Failed to parse JSON response from Timezone API: ${message}`,
      status: 502,
    };
  }

  const parseResult = upstreamTimezoneResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    tryApplyCacheDirectives(["google-timezone"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "upstream_validation_error",
      ok: false,
      reason: "Invalid response from Timezone API",
      status: 502,
    };
  }

  // Timezone lookups are stable; cache for 30 days, revalidate weekly, allow 1 day stale.
  tryApplyCacheDirectives(["google-timezone"], {
    expire: 60 * 60 * 24 * 30, // 30 days
    revalidate: 60 * 60 * 24 * 7, // 7 days
    stale: 60 * 60 * 24, // 1 day
  });

  return { data: parseResult.data, ok: true };
}

/**
 * Fetches and validates Google Routes API computeRoutes responses with Cache Components.
 *
 * Traffic-aware requests are cached briefly; traffic-unaware requests are cached longer.
 *
 * @param input - Routing request payload containing origin, destination, and optional routing preferences.
 * @returns Promise resolving to a CachedResult containing the validated ComputeRoutesResponse or error details.
 */
export async function computeRoutesCached(input: {
  destination: ComputeRoutesRequest["destination"];
  origin: ComputeRoutesRequest["origin"];
  routingPreference?: ComputeRoutesRequest["routingPreference"] | null;
  travelMode?: ComputeRoutesRequest["travelMode"] | null;
}): Promise<CachedResult<ComputeRoutesResponse>> {
  "use cache";

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    tryApplyCacheDirectives(["google-routes"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "google_maps_not_configured",
      ok: false,
      reason: "Google Maps API key is not configured",
      status: 500,
    };
  }

  const routingPreference =
    typeof input.routingPreference === "string"
      ? input.routingPreference
      : "TRAFFIC_UNAWARE";

  const fieldMask =
    "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.stepCount,routes.routeLabels";

  let response: Response;
  try {
    response = await postComputeRoutes({
      apiKey,
      body: {
        destination: input.destination,
        origin: input.origin,
        routingPreference,
        travelMode: input.travelMode ?? "DRIVE",
      },
      fieldMask,
    });
  } catch (err) {
    tryApplyCacheDirectives(["google-routes"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "external_api_error",
      ok: false,
      reason: err instanceof Error ? err.message : "Failed to compute route",
      status: 502,
    };
  }

  if (!response.ok) {
    const details = response.status < 500 ? await response.text() : "";
    tryApplyCacheDirectives(["google-routes"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      details: details.slice(0, 500),
      error: "upstream_error",
      ok: false,
      reason: `Routes API returned ${response.status}`,
      status: response.status >= 400 && response.status < 500 ? response.status : 502,
      upstreamStatus: response.status,
    };
  }

  let rawData: unknown;
  try {
    rawData = await response.json();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    tryApplyCacheDirectives(["google-routes"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "upstream_parse_error",
      ok: false,
      reason: `Failed to parse JSON response from Routes API: ${message}`,
      status: 502,
    };
  }

  const parseResult = upstreamRoutesResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    tryApplyCacheDirectives(["google-routes"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "upstream_validation_error",
      ok: false,
      reason: "Invalid response from Routes API",
      status: 502,
    };
  }

  const isTrafficAware = routingPreference.startsWith("TRAFFIC_AWARE");

  tryApplyCacheDirectives(["google-routes"], {
    expire: isTrafficAware ? 60 * 60 : 60 * 60 * 24 * 7, // 1h vs 7d
    revalidate: isTrafficAware ? 5 * 60 : 60 * 60 * 12, // 5m vs 12h
    stale: isTrafficAware ? 60 : 60 * 60, // 1m vs 1h
  });

  return { data: parseResult.data, ok: true };
}

/**
 * Fetches and validates Google Routes API computeRouteMatrix responses with Cache Components.
 *
 * @param input - Route matrix request payload containing origins, destinations, and optional travel mode.
 * @returns Promise resolving to a CachedResult containing the validated RouteMatrixResponse or error details.
 */
export async function computeRouteMatrixCached(input: {
  destinations: RouteMatrixRequest["destinations"];
  origins: RouteMatrixRequest["origins"];
  travelMode?: RouteMatrixRequest["travelMode"] | null;
}): Promise<CachedResult<RouteMatrixResponse>> {
  "use cache";

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    tryApplyCacheDirectives(["google-route-matrix"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "google_maps_not_configured",
      ok: false,
      reason: "Google Maps API key is not configured",
      status: 500,
    };
  }

  const fieldMask = "originIndex,destinationIndex,duration,distanceMeters,status";

  let response: Response;
  try {
    response = await postComputeRouteMatrix({
      apiKey,
      body: {
        destinations: input.destinations,
        origins: input.origins,
        travelMode: input.travelMode ?? "DRIVE",
      },
      fieldMask,
    });
  } catch (err) {
    tryApplyCacheDirectives(["google-route-matrix"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "external_api_error",
      ok: false,
      reason: err instanceof Error ? err.message : "Failed to compute route matrix",
      status: 502,
    };
  }

  if (!response.ok) {
    const details = response.status < 500 ? await response.text() : "";
    tryApplyCacheDirectives(["google-route-matrix"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      details: details.slice(0, 500),
      error: "upstream_error",
      ok: false,
      reason: `Routes API returned ${response.status}`,
      status: response.status >= 400 && response.status < 500 ? response.status : 502,
      upstreamStatus: response.status,
    };
  }

  let rawData: unknown[];
  try {
    rawData = await parseNdjsonResponse(response);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    tryApplyCacheDirectives(["google-route-matrix"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "upstream_parse_error",
      ok: false,
      reason: `Failed to parse NDJSON response: ${message}`,
      status: 502,
    };
  }

  const parseResult = upstreamRouteMatrixResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    tryApplyCacheDirectives(["google-route-matrix"], {
      expire: 60,
      revalidate: 30,
      stale: 10,
    });
    return {
      error: "upstream_validation_error",
      ok: false,
      reason: "Invalid response from Routes API",
      status: 502,
    };
  }

  tryApplyCacheDirectives(["google-route-matrix"], {
    expire: 60 * 60 * 24, // 1 day
    revalidate: 60 * 60 * 2, // 2 hours
    stale: 60 * 10, // 10 minutes
  });

  return { data: parseResult.data, ok: true };
}
