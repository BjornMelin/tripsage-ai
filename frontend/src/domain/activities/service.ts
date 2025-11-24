/**
 * @fileoverview Activities domain service orchestrating Google Places search,
 * caching, and optional AI/web fallback.
 *
 * Uses Supabase search_activities table as durable cache per SPEC-0030.
 */

import "server-only";

import { NotFoundError } from "@domain/activities/errors";
import type { ActivitySearchResult, ServiceContext } from "@domain/activities/types";
import type { Activity, ActivitySearchParams } from "@schemas/search";
import { activitySearchParamsSchema } from "@schemas/search";
import type { ToolCallOptions } from "ai";
import { webSearch } from "@/ai/tools/server/web-search";
import { hashInputForCache } from "@/lib/cache/hash";
import {
  buildActivitySearchQuery,
  getActivityDetailsFromPlaces,
  searchActivitiesWithPlaces,
} from "@/lib/google/places-activities";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const logger = createServerLogger("activities.service");

/**
 * Cache TTL for Google Places results (24 hours).
 */
const PLACES_CACHE_TTL_SECONDS = 24 * 60 * 60;

/**
 * Cache TTL for AI fallback results (6 hours).
 */
const AI_FALLBACK_CACHE_TTL_SECONDS = 6 * 60 * 60;

/**
 * Dependencies for the activities service.
 */
export interface ActivitiesServiceDeps {
  /** Supabase client factory. */
  supabase: () => Promise<TypedServerSupabase>;
}

/**
 * Activities service class.
 */
export class ActivitiesService {
  constructor(private readonly deps: ActivitiesServiceDeps) {}

  /**
   * Computes a normalized query hash for cache lookups.
   *
   * @param params - Activity search parameters.
   * @returns Normalized hash string.
   */
  private computeQueryHash(params: ActivitySearchParams): string {
    // Normalize params for consistent hashing
    const normalized = {
      adults: params.adults,
      category: params.category?.trim().toLowerCase(),
      children: params.children,
      date: params.date,
      destination: params.destination?.trim().toLowerCase(),
      difficulty: params.difficulty,
      duration: params.duration,
      indoor: params.indoor,
      infants: params.infants,
    };
    return hashInputForCache(normalized);
  }

  /**
   * Searches for activities with caching and optional AI fallback.
   *
   * @param params - Activity search parameters.
   * @param ctx - Service context (userId, locale, ip, etc.).
   * @returns Activity search result with metadata.
   */
  async search(
    params: ActivitySearchParams,
    ctx?: ServiceContext
  ): Promise<ActivitySearchResult> {
    return await withTelemetrySpan(
      "activities.search",
      {
        attributes: {
          hasCategory: Boolean(params.category),
          hasDestination: Boolean(params.destination),
        },
        redactKeys: ["destination"],
      },
      async (span) => {
        const parsedParams = activitySearchParamsSchema.safeParse(params);
        if (!parsedParams.success) {
          const destinationIssue = parsedParams.error.issues.find(
            (issue) => issue.path[0] === "destination"
          );
          if (destinationIssue) {
            throw new Error("Destination is required for activity search");
          }
          throw parsedParams.error;
        }
        const validatedParams = parsedParams.data;

        const userId = ctx?.userId;
        const queryHash = this.computeQueryHash(validatedParams);
        const destination = validatedParams.destination.trim();
        const activityType = validatedParams.category ?? null;

        // Check Supabase cache (authenticated users only)
        // Note: Database column names use snake_case (user_id, query_hash, activity_type, expires_at, created_at)
        let cacheResult: {
          data: {
            source: string;
            results: unknown;
          } | null;
          error: unknown;
        } | null = null;
        if (userId) {
          const supabase = await this.deps.supabase();
          cacheResult = await supabase
            .from("search_activities")
            .select("*")
            .eq("user_id", userId)
            .eq("destination", destination)
            .eq("query_hash", queryHash)
            .eq("activity_type", activityType ?? "")
            .gt("expires_at", new Date().toISOString())
            .order("created_at", { ascending: false })
            .limit(1)
            .maybeSingle();
        }

        if (cacheResult?.data) {
          span.addEvent("cache.hit", {
            queryHash,
            source: cacheResult.data.source,
          });
          logger.info("cache_hit", {
            destination,
            queryHash,
            source: cacheResult.data.source,
          });

          const cachedResults = cacheResult.data.results as Activity[];
          const cachedSource = cacheResult.data.source as
            | "googleplaces"
            | "ai_fallback"
            | "cached";

          return {
            activities: cachedResults,
            metadata: {
              cached: true,
              primarySource: cachedSource === "cached" ? "googleplaces" : cachedSource,
              sources: [cachedSource],
              total: cachedResults.length,
            },
          };
        }

        span.addEvent("cache.miss", { queryHash });
        logger.info("cache_miss", { destination, queryHash });

        // Perform Google Places search
        const searchQuery = buildActivitySearchQuery(
          destination,
          validatedParams.category
        );

        const placesActivities = await withTelemetrySpan(
          "activities.google_places.api",
          {
            attributes: { query: searchQuery },
            redactKeys: ["query"],
          },
          async () => await searchActivitiesWithPlaces(searchQuery, 20)
        );

        span.setAttribute("places.result_count", placesActivities.length);

        let activities: Activity[] = placesActivities;
        let primarySource: "googleplaces" | "ai_fallback" | "mixed" = "googleplaces";
        const sources: Array<"googleplaces" | "ai_fallback" | "cached"> = [
          "googleplaces",
        ];
        const notes: string[] = [];

        // Heuristic: trigger AI fallback if zero or very few results
        const shouldTriggerFallback =
          placesActivities.length === 0 ||
          (placesActivities.length < 3 && this.isPopularDestination(destination));

        let fallbackActivities: Activity[] = [];

        if (shouldTriggerFallback) {
          span.addEvent("activities.fallback.invoked");
          logger.info("fallback_invoked", {
            destination,
            placesCount: placesActivities.length,
          });

          try {
            // Call webSearch tool server-side
            const fallbackQuery = `things to do in ${destination}`;
            const webSearchResult = await webSearch.execute?.(
              {
                categories: null,
                fresh: false,
                freshness: null,
                limit: 5,
                location: null,
                query: fallbackQuery,
                region: null,
                scrapeOptions: null,
                sources: ["web"],
                tbs: null,
                timeoutMs: null,
                userId: userId ?? null,
              },
              {} as ToolCallOptions
            );

            if (!webSearchResult) {
              throw new Error("webSearch tool returned no result");
            }

            // Handle both direct result and async iterable
            const result =
              "results" in webSearchResult
                ? webSearchResult
                : await (async () => {
                    for await (const chunk of webSearchResult) {
                      return chunk;
                    }
                    throw new Error("No results from webSearch");
                  })();

            // Normalize web search results into Activity[] (best-effort)
            fallbackActivities = this.normalizeWebResultsToActivities(
              result.results,
              destination,
              validatedParams.date
            );

            if (fallbackActivities.length > 0) {
              primarySource = placesActivities.length > 0 ? "mixed" : "ai_fallback";
              sources.push("ai_fallback");
              activities = [...placesActivities, ...fallbackActivities];
              notes.push(
                "Some results are AI suggestions based on web content, not live availability"
              );

              // Persist fallback results separately with shorter TTL (authenticated users only)
              if (userId) {
                try {
                  const fallbackExpiresAt = new Date();
                  fallbackExpiresAt.setSeconds(
                    fallbackExpiresAt.getSeconds() + AI_FALLBACK_CACHE_TTL_SECONDS
                  );

                  const supabase = await this.deps.supabase();
                  await supabase.from("search_activities").insert({
                    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
                    activity_type: activityType,
                    destination,
                    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
                    expires_at: fallbackExpiresAt.toISOString(),
                    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
                    query_hash: `${queryHash}:fallback`,
                    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
                    query_parameters: { ...validatedParams, fallback: true },
                    results: fallbackActivities,
                    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
                    search_metadata: {
                      webResultsCount: result.results.length,
                      webSearchQuery: fallbackQuery,
                    },
                    source: "ai_fallback",
                    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
                    user_id: userId,
                  });
                } catch (insertError) {
                  logger.error("fallback_cache_insert_failed", {
                    destination,
                    error:
                      insertError instanceof Error
                        ? insertError.message
                        : String(insertError),
                  });
                  span.recordException(insertError as Error);
                  // Continue without caching - fallback results still returned
                }
              }
            }
          } catch (error) {
            logger.error("fallback_failed", {
              destination,
              error: error instanceof Error ? error.message : String(error),
            });
            span.recordException(error as Error);
            // Continue with Places results only
          }
        } else {
          span.addEvent("activities.fallback.suppressed", {
            count: placesActivities.length,
            reason: "sufficient_results",
          });
        }

        // Persist to Supabase cache (authenticated users only)
        if (userId) {
          try {
            const expiresAt = new Date();
            expiresAt.setSeconds(expiresAt.getSeconds() + PLACES_CACHE_TTL_SECONDS);

            const supabase = await this.deps.supabase();
            await supabase.from("search_activities").insert({
              // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
              activity_type: activityType,
              destination,
              // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
              expires_at: expiresAt.toISOString(),
              // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
              query_hash: queryHash,
              // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
              query_parameters: validatedParams,
              results: activities,
              // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
              search_metadata: {
                fallbackTriggered: shouldTriggerFallback,
                placesCount: placesActivities.length,
              },
              source: primarySource === "mixed" ? "googleplaces" : primarySource,
              // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
              user_id: userId,
            });
          } catch (insertError) {
            logger.error("cache_insert_failed", {
              destination,
              error:
                insertError instanceof Error
                  ? insertError.message
                  : String(insertError),
            });
            span.recordException(insertError as Error);
            // Continue without caching - results still returned
          }
        }

        return {
          activities,
          metadata: {
            cached: false,
            notes: notes.length > 0 ? notes : undefined,
            primarySource,
            sources,
            total: activities.length,
          },
        };
      }
    );
  }

  /**
   * Retrieves detailed activity information by Place ID.
   *
   * @param placeId - Google Place ID.
   * @param ctx - Service context.
   * @returns Activity object with full details.
   */
  async details(placeId: string, ctx?: ServiceContext): Promise<Activity> {
    return await withTelemetrySpan(
      "activities.details",
      {
        attributes: { placeId },
        redactKeys: [],
      },
      async (span) => {
        if (!placeId || placeId.trim().length === 0) {
          throw new Error("Place ID is required");
        }

        // Check cache for details (could be in search results)
        const supabase = await this.deps.supabase();
        const userId = ctx?.userId;

        // Try to find in recent search results (authenticated users only)
        // Note: Database column names use snake_case (user_id, expires_at, created_at)
        let cacheResult: {
          data: {
            results: unknown;
          } | null;
          error: unknown;
        } | null = null;
        if (userId) {
          cacheResult = await supabase
            .from("search_activities")
            .select("results")
            .eq("user_id", userId)
            .gt("expires_at", new Date().toISOString())
            .order("created_at", { ascending: false })
            .limit(10)
            .maybeSingle();
        }

        if (cacheResult?.data) {
          const results = cacheResult.data.results as Activity[];
          const cached = results.find((a) => a.id === placeId);
          if (cached) {
            span.addEvent("cache.hit", { placeId });
            return cached;
          }
        }

        span.addEvent("cache.miss", { placeId });

        // Fetch from Places API
        const activity = await getActivityDetailsFromPlaces(placeId);

        if (!activity) {
          throw new NotFoundError(`Activity not found for Place ID: ${placeId}`);
        }

        return activity;
      }
    );
  }

  /**
   * Simple heuristic to determine if a destination is "popular".
   *
   * Used to decide whether low Places result count should trigger AI fallback.
   * This is a basic implementation; can be enhanced with a whitelist or
   * external data source.
   *
   * @param destination - Destination string.
   * @returns True if destination is considered popular.
   */
  private isPopularDestination(destination: string): boolean {
    const normalized = destination.toLowerCase().trim();
    const popularDestinations = [
      "paris",
      "tokyo",
      "new york",
      "london",
      "rome",
      "barcelona",
      "amsterdam",
      "dubai",
      "sydney",
      "los angeles",
      "san francisco",
      "miami",
      "bangkok",
      "singapore",
      "hong kong",
    ];

    return popularDestinations.some((pop) => normalized.includes(pop));
  }

  /**
   * Normalizes web search results into Activity objects (best-effort).
   *
   * Extracts activity-like information from web search snippets and URLs.
   * This is a heuristic mapping and may not always produce high-quality results.
   *
   * @param webResults - Web search results from Firecrawl.
   * @param destination - Destination location.
   * @param date - Optional date string.
   * @returns Array of Activity objects (may be empty if normalization fails).
   */
  private normalizeWebResultsToActivities(
    webResults: Array<{
      url: string;
      title?: string;
      snippet?: string;
      publishedAt?: string;
    }>,
    destination: string,
    date?: string
  ): Activity[] {
    const activities: Activity[] = [];

    for (const result of webResults) {
      // Skip if no title or snippet
      if (!result.title && !result.snippet) {
        continue;
      }

      const name = result.title ?? "Activity";
      const description = result.snippet ?? `Activity in ${destination}`;

      // Extract activity type from title/snippet (heuristic)
      let type = "activity";
      const lowerName = name.toLowerCase();
      const lowerDesc = description.toLowerCase();

      if (lowerName.includes("museum") || lowerDesc.includes("museum")) {
        type = "museum";
      } else if (lowerName.includes("tour") || lowerDesc.includes("tour")) {
        type = "tour";
      } else if (lowerName.includes("park") || lowerDesc.includes("park")) {
        type = "park";
      } else if (lowerName.includes("restaurant") || lowerDesc.includes("restaurant")) {
        type = "restaurant";
      }

      // Default values for AI fallback activities
      const activity: Activity = {
        coordinates: undefined,
        date: date ?? new Date().toISOString().split("T")[0],
        description,
        duration: 120, // Default 2 hours
        id: `ai_fallback:${hashInputForCache(result.url)}`,
        images: undefined,
        location: destination,
        name,
        price: 2, // Default moderate price
        rating: 0, // No rating available
        type,
      };

      activities.push(activity);
    }

    return activities;
  }
}
