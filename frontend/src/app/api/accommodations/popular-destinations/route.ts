/**
 * @fileoverview API route returning cached popular hotel destinations.
 *
 * Returns personalized destinations based on user's search history if available,
 * falling back to global popular hotel destinations.
 */

import "server-only";

import type { User } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import type { TypedServerSupabase } from "@/lib/supabase/server";

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
type SearchHotelsDestinationRow = {
  destination: string | null;
};

const POPULAR_DESTINATIONS_TTL_SECONDS = 60 * 60; // 1 hour

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

/**
 * Resolves the user from the context or the database.
 *
 * @param supabase - Supabase client instance
 * @param userFromContext - User from the context
 * @returns Promise resolving to the user or null if no user is found
 */
async function resolveUser(
  supabase: TypedServerSupabase,
  userFromContext: User | null
): Promise<User | null> {
  if (userFromContext) return userFromContext;
  const result = await supabase.auth.getUser();
  if (result.error || !result.data?.user) return null;
  return result.data.user;
}

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

  if (error || !data || data.length === 0) return null;

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
    .map(([destination]) => ({
      avgPrice: undefined,
      city: destination,
      country: undefined,
    }));

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
  const resolvedUser = await resolveUser(supabase, contextUser);
  const cacheKey = resolvedUser?.id
    ? `popular-hotels:user:${resolvedUser.id}`
    : "popular-hotels:global";

  const cached = await getCachedJson<PopularDestination[]>(cacheKey);
  if (cached) {
    return NextResponse.json(cached, {
      headers: { "Cache-Control": "private, no-store" },
    });
  }

  if (resolvedUser?.id) {
    const personalized = await fetchPersonalizedDestinations(supabase, resolvedUser.id);
    if (personalized) {
      await setCachedJson(cacheKey, personalized, POPULAR_DESTINATIONS_TTL_SECONDS);
      return NextResponse.json(personalized, {
        headers: { "Cache-Control": "private, no-store" },
      });
    }
  }

  await setCachedJson(
    cacheKey,
    GLOBAL_POPULAR_DESTINATIONS,
    POPULAR_DESTINATIONS_TTL_SECONDS
  );
  return NextResponse.json(GLOBAL_POPULAR_DESTINATIONS, {
    headers: { "Cache-Control": "private, no-store" },
  });
});
