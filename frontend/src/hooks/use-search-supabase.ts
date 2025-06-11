/**
 * Search hooks with Supabase cache integration
 * Provides cached search results with automatic expiration
 */

import { useMemo, useCallback } from "react";
import { useUser } from "@supabase/auth-helpers-react";
import { useSupabase } from "@/lib/supabase/client";
import { useSupabaseQuery, useSupabaseInsert } from "./use-supabase-query";
import type { 
  SearchDestination, 
  SearchActivity, 
  SearchFlight, 
  SearchHotel,
  InsertTables 
} from "@/lib/supabase/database.types";

export interface SearchCacheOptions {
  enableCache?: boolean;
  cacheExpiry?: number; // hours
  forceRefresh?: boolean;
}

/**
 * Utility function to generate cache hash
 */
function generateCacheHash(query: any): string {
  return btoa(JSON.stringify(query)).replace(/[^a-zA-Z0-9]/g, "");
}

/**
 * Hook for destination search with caching
 */
export function useDestinationSearch(
  query: string,
  options: SearchCacheOptions = {}
) {
  const user = useUser();
  const supabase = useSupabase();
  const { enableCache = true, cacheExpiry = 24, forceRefresh = false } = options;

  const queryHash = useMemo(() => generateCacheHash({ query }), [query]);

  // Check cache first
  const cacheQuery = useSupabaseQuery(
    "search_destinations",
    (q) => q
      .eq("user_id", user?.id)
      .eq("query_hash", queryHash)
      .gt("expires_at", new Date().toISOString())
      .order("created_at", { ascending: false })
      .limit(1),
    {
      enabled: !!user?.id && !!query && enableCache && !forceRefresh,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  const insertCacheMutation = useSupabaseInsert("search_destinations");

  const searchDestinations = useCallback(async (searchQuery: string) => {
    if (!user?.id) throw new Error("User not authenticated");

    try {
      // Call external API (Google Maps, etc.)
      const response = await fetch("/api/search/destinations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!response.ok) {
        throw new Error("Search failed");
      }

      const results = await response.json();

      // Cache the results
      if (enableCache) {
        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + cacheExpiry);

        const cacheData: InsertTables<"search_destinations"> = {
          user_id: user.id,
          query: searchQuery,
          query_hash: generateCacheHash({ query: searchQuery }),
          results,
          source: "google_maps",
          search_metadata: {
            timestamp: new Date().toISOString(),
            user_agent: navigator.userAgent,
          },
          expires_at: expiresAt.toISOString(),
        };

        await insertCacheMutation.mutateAsync(cacheData);
      }

      return results;
    } catch (error) {
      console.error("❌ Destination search failed:", error);
      throw error;
    }
  }, [user?.id, enableCache, cacheExpiry, insertCacheMutation]);

  const cachedResults = cacheQuery.data?.[0]?.results;
  const isFromCache = !!cachedResults && !forceRefresh;

  return {
    results: cachedResults || null,
    searchDestinations,
    isLoading: cacheQuery.isLoading,
    error: cacheQuery.error,
    isFromCache,
    cacheAge: cacheQuery.data?.[0]?.created_at,
  };
}

/**
 * Hook for activity search with caching
 */
export function useActivitySearch(
  destination: string,
  activityType?: string,
  options: SearchCacheOptions = {}
) {
  const user = useUser();
  const supabase = useSupabase();
  const { enableCache = true, cacheExpiry = 12, forceRefresh = false } = options;

  const queryParams = useMemo(() => ({ destination, activityType }), [destination, activityType]);
  const queryHash = useMemo(() => generateCacheHash(queryParams), [queryParams]);

  // Check cache first
  const cacheQuery = useSupabaseQuery(
    "search_activities",
    (q) => q
      .eq("user_id", user?.id)
      .eq("query_hash", queryHash)
      .gt("expires_at", new Date().toISOString())
      .order("created_at", { ascending: false })
      .limit(1),
    {
      enabled: !!user?.id && !!destination && enableCache && !forceRefresh,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  const insertCacheMutation = useSupabaseInsert("search_activities");

  const searchActivities = useCallback(async (searchDestination: string, type?: string) => {
    if (!user?.id) throw new Error("User not authenticated");

    try {
      const response = await fetch("/api/search/activities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          destination: searchDestination, 
          activityType: type 
        }),
      });

      if (!response.ok) {
        throw new Error("Activity search failed");
      }

      const results = await response.json();

      // Cache the results
      if (enableCache) {
        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + cacheExpiry);

        const cacheData: InsertTables<"search_activities"> = {
          user_id: user.id,
          destination: searchDestination,
          activity_type: type || null,
          query_parameters: { destination: searchDestination, activityType: type },
          query_hash: generateCacheHash({ destination: searchDestination, activityType: type }),
          results,
          source: "viator",
          search_metadata: {
            timestamp: new Date().toISOString(),
            filters_applied: type ? [type] : [],
          },
          expires_at: expiresAt.toISOString(),
        };

        await insertCacheMutation.mutateAsync(cacheData);
      }

      return results;
    } catch (error) {
      console.error("❌ Activity search failed:", error);
      throw error;
    }
  }, [user?.id, enableCache, cacheExpiry, insertCacheMutation]);

  const cachedResults = cacheQuery.data?.[0]?.results;
  const isFromCache = !!cachedResults && !forceRefresh;

  return {
    results: cachedResults || null,
    searchActivities,
    isLoading: cacheQuery.isLoading,
    error: cacheQuery.error,
    isFromCache,
    cacheAge: cacheQuery.data?.[0]?.created_at,
  };
}

/**
 * Hook for flight search with caching
 */
export function useFlightSearch(
  origin: string,
  destination: string,
  departureDate: string,
  returnDate?: string,
  passengers = 1,
  cabinClass = "economy" as const,
  options: SearchCacheOptions = {}
) {
  const user = useUser();
  const supabase = useSupabase();
  const { enableCache = true, cacheExpiry = 1, forceRefresh = false } = options; // 1 hour cache for flights

  const queryParams = useMemo(() => ({
    origin,
    destination,
    departureDate,
    returnDate,
    passengers,
    cabinClass,
  }), [origin, destination, departureDate, returnDate, passengers, cabinClass]);

  const queryHash = useMemo(() => generateCacheHash(queryParams), [queryParams]);

  // Check cache first
  const cacheQuery = useSupabaseQuery(
    "search_flights",
    (q) => q
      .eq("user_id", user?.id)
      .eq("query_hash", queryHash)
      .gt("expires_at", new Date().toISOString())
      .order("created_at", { ascending: false })
      .limit(1),
    {
      enabled: !!user?.id && !!origin && !!destination && !!departureDate && enableCache && !forceRefresh,
      staleTime: 30 * 1000, // 30 seconds
    }
  );

  const insertCacheMutation = useSupabaseInsert("search_flights");

  const searchFlights = useCallback(async (searchParams: typeof queryParams) => {
    if (!user?.id) throw new Error("User not authenticated");

    try {
      const response = await fetch("/api/search/flights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(searchParams),
      });

      if (!response.ok) {
        throw new Error("Flight search failed");
      }

      const results = await response.json();

      // Cache the results
      if (enableCache) {
        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + cacheExpiry);

        const cacheData: InsertTables<"search_flights"> = {
          user_id: user.id,
          origin: searchParams.origin,
          destination: searchParams.destination,
          departure_date: searchParams.departureDate,
          return_date: searchParams.returnDate || null,
          passengers: searchParams.passengers,
          cabin_class: searchParams.cabinClass,
          query_parameters: searchParams,
          query_hash: generateCacheHash(searchParams),
          results,
          source: "duffel",
          search_metadata: {
            timestamp: new Date().toISOString(),
            search_duration_ms: Date.now(),
          },
          expires_at: expiresAt.toISOString(),
        };

        await insertCacheMutation.mutateAsync(cacheData);
      }

      return results;
    } catch (error) {
      console.error("❌ Flight search failed:", error);
      throw error;
    }
  }, [user?.id, enableCache, cacheExpiry, insertCacheMutation]);

  const cachedResults = cacheQuery.data?.[0]?.results;
  const isFromCache = !!cachedResults && !forceRefresh;

  return {
    results: cachedResults || null,
    searchFlights,
    isLoading: cacheQuery.isLoading,
    error: cacheQuery.error,
    isFromCache,
    cacheAge: cacheQuery.data?.[0]?.created_at,
  };
}

/**
 * Hook for hotel search with caching
 */
export function useHotelSearch(
  destination: string,
  checkInDate: string,
  checkOutDate: string,
  guests = 1,
  rooms = 1,
  options: SearchCacheOptions = {}
) {
  const user = useUser();
  const supabase = useSupabase();
  const { enableCache = true, cacheExpiry = 6, forceRefresh = false } = options; // 6 hour cache for hotels

  const queryParams = useMemo(() => ({
    destination,
    checkInDate,
    checkOutDate,
    guests,
    rooms,
  }), [destination, checkInDate, checkOutDate, guests, rooms]);

  const queryHash = useMemo(() => generateCacheHash(queryParams), [queryParams]);

  // Check cache first
  const cacheQuery = useSupabaseQuery(
    "search_hotels",
    (q) => q
      .eq("user_id", user?.id)
      .eq("query_hash", queryHash)
      .gt("expires_at", new Date().toISOString())
      .order("created_at", { ascending: false })
      .limit(1),
    {
      enabled: !!user?.id && !!destination && !!checkInDate && !!checkOutDate && enableCache && !forceRefresh,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  const insertCacheMutation = useSupabaseInsert("search_hotels");

  const searchHotels = useCallback(async (searchParams: typeof queryParams) => {
    if (!user?.id) throw new Error("User not authenticated");

    try {
      const response = await fetch("/api/search/hotels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(searchParams),
      });

      if (!response.ok) {
        throw new Error("Hotel search failed");
      }

      const results = await response.json();

      // Cache the results
      if (enableCache) {
        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + cacheExpiry);

        const cacheData: InsertTables<"search_hotels"> = {
          user_id: user.id,
          destination: searchParams.destination,
          check_in_date: searchParams.checkInDate,
          check_out_date: searchParams.checkOutDate,
          guests: searchParams.guests,
          rooms: searchParams.rooms,
          query_parameters: searchParams,
          query_hash: generateCacheHash(searchParams),
          results,
          source: "booking",
          search_metadata: {
            timestamp: new Date().toISOString(),
            nights: Math.ceil(
              (new Date(searchParams.checkOutDate).getTime() - 
               new Date(searchParams.checkInDate).getTime()) / (1000 * 60 * 60 * 24)
            ),
          },
          expires_at: expiresAt.toISOString(),
        };

        await insertCacheMutation.mutateAsync(cacheData);
      }

      return results;
    } catch (error) {
      console.error("❌ Hotel search failed:", error);
      throw error;
    }
  }, [user?.id, enableCache, cacheExpiry, insertCacheMutation]);

  const cachedResults = cacheQuery.data?.[0]?.results;
  const isFromCache = !!cachedResults && !forceRefresh;

  return {
    results: cachedResults || null,
    searchHotels,
    isLoading: cacheQuery.isLoading,
    error: cacheQuery.error,
    isFromCache,
    cacheAge: cacheQuery.data?.[0]?.created_at,
  };
}

/**
 * Hook for search history and analytics
 */
export function useSearchHistory() {
  const user = useUser();

  const destinationHistory = useSupabaseQuery(
    "search_destinations",
    (q) => q
      .eq("user_id", user?.id)
      .order("created_at", { ascending: false })
      .limit(20),
    {
      enabled: !!user?.id,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  const flightHistory = useSupabaseQuery(
    "search_flights",
    (q) => q
      .eq("user_id", user?.id)
      .order("created_at", { ascending: false })
      .limit(20),
    {
      enabled: !!user?.id,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  const hotelHistory = useSupabaseQuery(
    "search_hotels",
    (q) => q
      .eq("user_id", user?.id)
      .order("created_at", { ascending: false })
      .limit(20),
    {
      enabled: !!user?.id,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  return {
    destinationHistory: destinationHistory.data || [],
    flightHistory: flightHistory.data || [],
    hotelHistory: hotelHistory.data || [],
    isLoading: destinationHistory.isLoading || flightHistory.isLoading || hotelHistory.isLoading,
  };
}