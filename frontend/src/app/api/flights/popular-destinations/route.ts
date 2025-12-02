/**
 * @fileoverview API route returning cached popular flight destinations.
 */

import "server-only";

import type { User } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/** Popular destination returned to the client. */
interface PopularDestination {
  code: string;
  name: string;
  savings?: string;
  country?: string;
}

/** Row from the search_flights table. */
type SearchFlightsDestinationRow = {
  destination: string | null;
};

const POPULAR_DESTINATIONS_TTL_SECONDS = 60 * 60; // 1 hour

/** Global popular destinations. */
const GLOBAL_POPULAR_DESTINATIONS: PopularDestination[] = [
  { code: "NYC", country: "USA", name: "New York", savings: "$127" },
  { code: "LAX", country: "USA", name: "Los Angeles", savings: "$89" },
  { code: "LHR", country: "UK", name: "London", savings: "$234" },
  { code: "NRT", country: "Japan", name: "Tokyo", savings: "$298" },
  { code: "CDG", country: "France", name: "Paris", savings: "$156" },
  { code: "DXB", country: "UAE", name: "Dubai", savings: "$312" },
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
 * Fetches personalized destinations for a user from the search_flights table.
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
    .from("search_flights")
    .select("destination")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(100)
    .returns<SearchFlightsDestinationRow[]>();

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
      code: destination,
      name: destination,
    }));

  return destinations.length > 0 ? destinations : null;
}

/**
 * Handles GET /api/flights/popular-destinations.
 *
 * @param _req - Request object
 * @param contextUser - User from the context
 * @param supabase - Supabase client instance
 * @returns Promise resolving to a NextResponse with the popular destinations
 */
export const GET = withApiGuards({
  auth: false,
  rateLimit: "flights:popular-destinations",
  telemetry: "flights.popular_destinations",
})(async (_req, { user: contextUser, supabase }) => {
  const resolvedUser = await resolveUser(supabase, contextUser);
  const cacheKey = resolvedUser?.id
    ? `popular-destinations:user:${resolvedUser.id}`
    : "popular-destinations:global";

  const cached = await getCachedJson<PopularDestination[]>(cacheKey);
  if (cached) {
    return NextResponse.json(cached);
  }

  if (resolvedUser?.id) {
    const personalized = await fetchPersonalizedDestinations(supabase, resolvedUser.id);
    if (personalized) {
      await setCachedJson(cacheKey, personalized, POPULAR_DESTINATIONS_TTL_SECONDS);
      return NextResponse.json(personalized);
    }
  }

  await setCachedJson(
    cacheKey,
    GLOBAL_POPULAR_DESTINATIONS,
    POPULAR_DESTINATIONS_TTL_SECONDS
  );
  return NextResponse.json(GLOBAL_POPULAR_DESTINATIONS);
});
