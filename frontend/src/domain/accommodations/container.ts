/**
 * @fileoverview Dependency container for accommodations domain.
 *
 * Centralizes construction of the accommodations service so callers (AI tools, routes)
 * do not hard-wire provider/configuration at import time.
 */

import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "@domain/accommodations/constants";
import { ExpediaProviderAdapter } from "@domain/accommodations/providers/expedia-adapter";
import { AccommodationsService } from "@domain/accommodations/service";
import { Ratelimit } from "@upstash/ratelimit";
import { getRedis } from "@/lib/redis";
import { createServerSupabase } from "@/lib/supabase/server";

let singleton: AccommodationsService | undefined;

/**
 * Returns a singleton AccommodationsService configured with Expedia adapter,
 * cache TTL, rate limit, and Supabase factory.
 */
export function getAccommodationsService(): AccommodationsService {
  if (singleton) return singleton;

  const redis = getRedis();
  const rateLimiter = redis
    ? new Ratelimit({
        analytics: false,
        limiter: Ratelimit.slidingWindow(10, "1 m"),
        prefix: "ratelimit:accommodations:service",
        redis,
      })
    : undefined;

  const provider = new ExpediaProviderAdapter();

  singleton = new AccommodationsService({
    cacheTtlSeconds: ACCOM_SEARCH_CACHE_TTL_SECONDS,
    provider,
    rateLimiter,
    supabase: createServerSupabase,
  });

  return singleton;
}
