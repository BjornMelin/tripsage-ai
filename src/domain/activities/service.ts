/**
 * @fileoverview Activities domain service orchestrating Places search, caching, and optional web fallback.
 */

import "server-only";

import { NotFoundError } from "@domain/activities/errors";
import type { ActivitySearchResult, ServiceContext } from "@domain/activities/types";
import type { Activity, ActivitySearchParams } from "@schemas/search";
import { activitySearchParamsSchema } from "@schemas/search";

/**
 * Cache TTL for Places-backed activity search results (24 hours).
 */
const PLACES_CACHE_TTL_SECONDS = 24 * 60 * 60;

const AI_FALLBACK_DEFAULT_DURATION_MINUTES = 120;
const AI_FALLBACK_DEFAULT_PRICE_TIER = 2;
const AI_FALLBACK_DEFAULT_RATING = 0;

export type ActivitiesLogger = {
  info: (message: string, meta?: Record<string, unknown>) => void;
  warn: (message: string, meta?: Record<string, unknown>) => void;
  error: (message: string, meta?: Record<string, unknown>) => void;
};

type TelemetryAttributes = Record<string, string | number | boolean>;

export type ActivitiesTelemetrySpan = {
  addEvent: (name: string, attributes?: TelemetryAttributes) => void;
  recordException: (error: Error) => void;
  setAttribute: (key: string, value: string | number | boolean) => void;
};

export type ActivitiesTelemetryOptions = {
  attributes?: TelemetryAttributes;
  redactKeys?: string[];
};

export type ActivitiesTelemetry = {
  withSpan: <T>(
    name: string,
    options: ActivitiesTelemetryOptions,
    fn: (span: ActivitiesTelemetrySpan) => Promise<T>
  ) => Promise<T>;
};

export type WebSearchSource = {
  url: string;
  title?: string;
  snippet?: string;
  publishedAt?: string;
};

export type WebSearchResult = {
  results: WebSearchSource[];
};

export type WebSearchFn = (input: {
  query: string;
  limit: number;
  toolCallId: string;
  userId?: string;
}) => Promise<WebSearchResult | null>;

export type PlacesActivitiesAdapter = {
  buildSearchQuery: (destination: string, category?: string) => string;
  search: (query: string, limit: number) => Promise<Activity[]>;
  getDetails: (placeId: string) => Promise<Activity | null>;
};

export type ActivitiesCacheSource = "googleplaces" | "ai_fallback" | "cached";

export type ActivitiesCache = {
  getSearch: (input: {
    activityType: string | null;
    destination: string;
    nowIso: string;
    queryHash: string;
    userId: string;
  }) => Promise<null | { source: ActivitiesCacheSource; results: Activity[] }>;
  putSearch: (input: {
    activityType: string | null;
    destination: string;
    expiresAtIso: string;
    queryHash: string;
    queryParameters: ActivitySearchParams;
    results: Activity[];
    searchMetadata: Record<string, unknown>;
    source: ActivitiesCacheSource;
    userId: string;
  }) => Promise<void>;
  findActivityInRecentSearches: (input: {
    nowIso: string;
    placeId: string;
    userId: string;
  }) => Promise<Activity | null>;
};

export type ActivitiesClock = {
  now: () => number;
  todayIsoDate: () => string;
};

/**
 * Dependencies for the activities service.
 */
export interface ActivitiesServiceDeps {
  cache?: ActivitiesCache;
  clock?: ActivitiesClock;
  hashInput: (input: unknown) => string;
  logger?: ActivitiesLogger;
  places: PlacesActivitiesAdapter;
  telemetry?: ActivitiesTelemetry;
  webSearch?: WebSearchFn;
}

const noopLogger: ActivitiesLogger = {
  error: () => undefined,
  info: () => undefined,
  warn: () => undefined,
};

const noopSpan: ActivitiesTelemetrySpan = {
  addEvent: () => undefined,
  recordException: () => undefined,
  setAttribute: () => undefined,
};

const noopTelemetry: ActivitiesTelemetry = {
  withSpan: async <T>(
    _name: string,
    _options: ActivitiesTelemetryOptions,
    fn: (span: ActivitiesTelemetrySpan) => Promise<T>
  ): Promise<T> => fn(noopSpan),
};

const defaultClock: ActivitiesClock = {
  now: () => Date.now(),
  todayIsoDate: () => new Date().toISOString().split("T")[0] ?? "1970-01-01",
};

/**
 * Activities service class.
 */
export class ActivitiesService {
  private readonly clock: ActivitiesClock;
  private readonly logger: ActivitiesLogger;
  private readonly telemetry: ActivitiesTelemetry;

  constructor(private readonly deps: ActivitiesServiceDeps) {
    this.clock = deps.clock ?? defaultClock;
    this.logger = deps.logger ?? noopLogger;
    this.telemetry = deps.telemetry ?? noopTelemetry;
  }

  /**
   * Computes a normalized query hash for cache lookups.
   *
   * @param params - Activity search parameters.
   * @returns Normalized hash string.
   */
  private computeQueryHash(params: ActivitySearchParams): string {
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
    return this.deps.hashInput(normalized);
  }

  private nowIso(): string {
    return new Date(this.clock.now()).toISOString();
  }

  /**
   * Searches for activities with caching and optional web fallback.
   *
   * @param params - Activity search parameters.
   * @param ctx - Service context (userId, locale, ip, etc.).
   * @returns Activity search result with metadata.
   */
  async search(
    params: ActivitySearchParams,
    ctx?: ServiceContext
  ): Promise<ActivitySearchResult> {
    return await this.telemetry.withSpan(
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

        const userId = ctx?.userId?.trim() || undefined;
        const queryHash = this.computeQueryHash(validatedParams);
        const destination = validatedParams.destination.trim();
        const activityType = validatedParams.category ?? null;

        if (userId && this.deps.cache) {
          const cached = await this.deps.cache.getSearch({
            activityType,
            destination,
            nowIso: this.nowIso(),
            queryHash,
            userId,
          });
          if (cached) {
            span.addEvent("cache.hit", { queryHash, source: cached.source });
            this.logger.info("cache_hit", {
              destination,
              queryHash,
              source: cached.source,
            });

            return {
              activities: cached.results,
              metadata: {
                cached: true,
                primarySource:
                  cached.source === "cached" ? "googleplaces" : cached.source,
                sources: [cached.source],
                total: cached.results.length,
              },
            };
          }
        }

        span.addEvent("cache.miss", { queryHash });
        this.logger.info("cache_miss", { destination, queryHash });

        const searchQuery = this.deps.places.buildSearchQuery(
          destination,
          validatedParams.category
        );

        const placesActivities = await this.telemetry.withSpan(
          "activities.google_places.api",
          {
            attributes: { query: searchQuery },
            redactKeys: ["query"],
          },
          async () => await this.deps.places.search(searchQuery, 20)
        );

        span.setAttribute("places.result_count", placesActivities.length);

        let activities: Activity[] = placesActivities;
        let primarySource: "googleplaces" | "ai_fallback" | "mixed" = "googleplaces";
        const sources: Array<"googleplaces" | "ai_fallback" | "cached"> = [
          "googleplaces",
        ];
        const notes: string[] = [];

        const shouldTriggerFallback =
          placesActivities.length === 0 ||
          (placesActivities.length < 3 && this.isPopularDestination(destination));

        let fallbackActivities: Activity[] = [];

        if (shouldTriggerFallback) {
          span.addEvent("activities.fallback.invoked");
          this.logger.info("fallback_invoked", {
            destination,
            placesCount: placesActivities.length,
          });

          if (this.deps.webSearch) {
            try {
              const fallbackQuery = `things to do in ${destination}`;
              const webSearchResult = await this.deps.webSearch({
                limit: 5,
                query: fallbackQuery,
                toolCallId: `activities:webSearch:${queryHash}`,
                userId,
              });
              if (!webSearchResult) {
                throw new Error("webSearch returned no result");
              }

              fallbackActivities = this.normalizeWebResultsToActivities(
                webSearchResult.results,
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
              }
            } catch (error) {
              this.logger.error("fallback_failed", {
                destination,
                error: error instanceof Error ? error.message : String(error),
              });
              span.recordException(
                error instanceof Error ? error : new Error(String(error))
              );
            }
          } else {
            span.addEvent("activities.fallback.skipped", {
              reason: "web_search_unavailable",
            });
          }
        } else {
          span.addEvent("activities.fallback.suppressed", {
            count: placesActivities.length,
            reason: "sufficient_results",
          });
        }

        if (userId && this.deps.cache) {
          try {
            const expiresAt = new Date(this.clock.now());
            expiresAt.setSeconds(expiresAt.getSeconds() + PLACES_CACHE_TTL_SECONDS);

            await this.deps.cache.putSearch({
              activityType,
              destination,
              expiresAtIso: expiresAt.toISOString(),
              queryHash,
              queryParameters: validatedParams,
              results: activities,
              searchMetadata: {
                fallbackCount: fallbackActivities.length,
                fallbackTriggered: shouldTriggerFallback,
                placesCount: placesActivities.length,
              },
              source: primarySource === "mixed" ? "googleplaces" : primarySource,
              userId,
            });
          } catch (error) {
            this.logger.error("cache_insert_failed", {
              destination,
              error: error instanceof Error ? error.message : String(error),
            });
            span.recordException(
              error instanceof Error ? error : new Error(String(error))
            );
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
    return await this.telemetry.withSpan(
      "activities.details",
      {
        attributes: { placeId },
        redactKeys: [],
      },
      async (span) => {
        if (!placeId || placeId.trim().length === 0) {
          throw new Error("Place ID is required");
        }

        const userId = ctx?.userId?.trim() || undefined;
        if (userId && this.deps.cache) {
          const cached = await this.deps.cache.findActivityInRecentSearches({
            nowIso: this.nowIso(),
            placeId,
            userId,
          });
          if (cached) {
            span.addEvent("cache.hit", { placeId });
            return cached;
          }
        }

        span.addEvent("cache.miss", { placeId });

        const activity = await this.deps.places.getDetails(placeId);
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
   * Used to decide whether low Places result count should trigger fallback.
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
   *
   * @param webResults - Web search results.
   * @param destination - Destination location.
   * @param date - Optional date string.
   * @returns Array of Activity objects (may be empty if normalization fails).
   */
  private normalizeWebResultsToActivities(
    webResults: WebSearchSource[],
    destination: string,
    date?: string
  ): Activity[] {
    const activities: Activity[] = [];

    for (const result of webResults) {
      if (!result.title && !result.snippet) {
        continue;
      }

      const name = result.title ?? "Activity";
      const description = result.snippet ?? `Activity in ${destination}`;

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

      activities.push({
        coordinates: undefined,
        date: date ?? this.clock.todayIsoDate(),
        description,
        duration: AI_FALLBACK_DEFAULT_DURATION_MINUTES,
        id: `ai_fallback:${this.deps.hashInput(result.url)}`,
        images: undefined,
        location: destination,
        name,
        price: AI_FALLBACK_DEFAULT_PRICE_TIER,
        rating: AI_FALLBACK_DEFAULT_RATING,
        type,
      });
    }

    return activities;
  }
}
