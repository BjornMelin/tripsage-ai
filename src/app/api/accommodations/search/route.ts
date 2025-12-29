/**
 * @fileoverview POST /api/accommodations/search route handler.
 */

import "server-only";

import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "@domain/accommodations/constants";
import { AmadeusProviderAdapter } from "@domain/accommodations/providers/amadeus-adapter";
import { AccommodationsService } from "@domain/accommodations/service";
import { accommodationSearchInputSchema } from "@schemas/accommodations";
import { withApiGuards } from "@/lib/api/factory";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { bumpTag, versionedKey } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { enrichHotelListingWithPlaces } from "@/lib/google/places-enrichment";
import { resolveLocationToLatLng } from "@/lib/google/places-geocoding";
import { retryWithBackoff } from "@/lib/http/retry";
import { getCurrentUser } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

export const POST = withApiGuards({
  auth: false, // Allow anonymous searches
  rateLimit: "accommodations:search",
  schema: accommodationSearchInputSchema,
  telemetry: "accommodations.search",
})(async (_req, { supabase }, body) => {
  const userResult = await getCurrentUser(supabase);

  const service = new AccommodationsService({
    bumpTag,
    cacheTtlSeconds: ACCOM_SEARCH_CACHE_TTL_SECONDS,
    canonicalizeParamsForCache,
    enrichHotelListingWithPlaces,
    getCachedJson,
    provider: new AmadeusProviderAdapter(),
    resolveLocationToLatLng,
    retryWithBackoff,
    setCachedJson,
    supabase: async () => supabase,
    versionedKey,
    withTelemetrySpan,
  });

  const result = await service.search(body, {
    userId: userResult.user?.id ?? undefined,
  });

  return Response.json(result);
});
