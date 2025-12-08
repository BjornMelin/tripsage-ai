/**
 * @fileoverview API route returning cached popular hotel destinations.
 *
 * Returns personalized destinations based on user's search history if available,
 * falling back to global popular hotel destinations.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

/** Popular hotel destination returned to the client. */
interface PopularDestination {
  /** City or destination name */
  city: string;
  /** Country name */
  country?: string;
  /** Average nightly price */
  avgPrice?: string;
  /** Optional image URL */
  imageUrl?: string;
}

/** Row from the search_hotels table. */
type SearchHotelsDestinationRow = Pick<
  Database["public"]["Tables"]["search_hotels"]["Row"],
  "destination"
>;

const POPULAR_DESTINATIONS_TTL_SECONDS = 60 * 60; // 1 hour
const POPULAR_HOTELS_GLOBAL_CACHE_KEY = "popular-hotels:global";
const logger = createServerLogger("api.accommodations.popular-destinations");

/** Global popular hotel destinations with typical pricing. */
const GLOBAL_POPULAR_DESTINATIONS: PopularDestination[] = [
  { avgPrice: "$245", city: "Paris", country: "France" },
  { avgPrice: "$189", city: "Tokyo", country: "Japan" },
  { avgPrice: "$312", city: "New York", country: "USA" },
  { avgPrice: "$278", city: "London", country: "UK" },
  { avgPrice: "$156", city: "Barcelona", country: "Spain" },
  { avgPrice: "$198", city: "Dubai", country: "UAE" },
  { avgPrice: "$167", city: "Rome", country: "Italy" },
  { avgPrice: "$89", city: "Bangkok", country: "Thailand" },
  { avgPrice: "$234", city: "Sydney", country: "Australia" },
  { avgPrice: "$201", city: "Amsterdam", country: "Netherlands" },
];

const GLOBAL_POPULAR_DESTINATIONS_BY_CITY = new Map(
  GLOBAL_POPULAR_DESTINATIONS.map(
    (destination) =>
      [destination.city.toLowerCase(), destination] satisfies [
        string,
        PopularDestination,
      ]
  )
);

/**
 * Fetches personalized hotel destinations for a user from the search_hotels table.
 *
 * @param supabase - Supabase client instance
 * @param userId - User ID
 * @returns Promise resolving to an array of PopularDestination
 *          objects or null if no destinations are found
 */
async function fetchPersonalizedDestinations(
  supabase: TypedServerSupabase,
  userId: string
): Promise<PopularDestination[] | null> {
  const { data, error } = await supabase
    .from("search_hotels")
    .select("destination")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(100)
    .returns<SearchHotelsDestinationRow[]>();

  if (error) {
    const safeError = error?.message ?? "search_hotels_query_failed";
    logger.error("popular_destinations.search_hotels_failed", { error: safeError });
    return null;
  }
  if (!data || data.length === 0) return null;

  const destinationCounts = new Map<string, number>();
  for (const row of data) {
    if (!row.destination) continue;
    destinationCounts.set(
      row.destination,
      (destinationCounts.get(row.destination) ?? 0) + 1
    );
  }

  const destinations = Array.from(destinationCounts.entries())
    .sort(([, countA], [, countB]) => countB - countA)
    .slice(0, 10)
    .map(([destination]) => {
      const fallback = GLOBAL_POPULAR_DESTINATIONS_BY_CITY.get(
        destination.toLowerCase()
      );
      return {
        avgPrice: fallback?.avgPrice,
        city: destination,
        country: fallback?.country,
      } satisfies PopularDestination;
    });

  return destinations.length > 0 ? destinations : null;
}

/**
 * Handles GET /api/accommodations/popular-destinations.
 *
 * Returns personalized destinations if user has search history,
 * otherwise returns global popular destinations.
 *
 * @param _req - Request object
 * @param contextUser - User from the context
 * @param supabase - Supabase client instance
 * @returns Promise resolving to a NextResponse with the popular destinations
 */
// Note: personalization is user-scoped; this route now requires auth to avoid
// any accidental leakage of user-derived history. Responses remain private.
export const GET = withApiGuards({
  auth: true,
  rateLimit: "accommodations:popular-destinations",
  telemetry: "accommodations.popular_destinations",
})(async (_req, { user: contextUser, supabase }) => {
  if (!contextUser) {
    throw new Error("User context is required but missing");
  }
  const resolvedUser = contextUser; // Now guaranteed non-null
  const userCacheKey = `popular-hotels:user:${resolvedUser.id}`;

  const cachedPersonalized = await getCachedJson<PopularDestination[]>(userCacheKey);
  if (cachedPersonalized) {
    return NextResponse.json(cachedPersonalized, {
      headers: { "Cache-Control": "private, no-store" },
    });
  }

  const cachedGlobal = await getCachedJson<PopularDestination[]>(
    POPULAR_HOTELS_GLOBAL_CACHE_KEY
  );
  if (cachedGlobal) {
    return NextResponse.json(cachedGlobal, {
      headers: { "Cache-Control": "private, no-store" },
    });
  }

  const personalized = await fetchPersonalizedDestinations(supabase, resolvedUser.id);
  if (personalized) {
    await setCachedJson(userCacheKey, personalized, POPULAR_DESTINATIONS_TTL_SECONDS);
    return NextResponse.json(personalized, {
      headers: { "Cache-Control": "private, no-store" },
    });
  }

  await setCachedJson(
    POPULAR_HOTELS_GLOBAL_CACHE_KEY,
    GLOBAL_POPULAR_DESTINATIONS,
    POPULAR_DESTINATIONS_TTL_SECONDS
  );
  return NextResponse.json(GLOBAL_POPULAR_DESTINATIONS, {
    headers: { "Cache-Control": "private, no-store" },
  });
});
