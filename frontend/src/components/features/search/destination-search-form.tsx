/**
 * @fileoverview Destination search form component for searching destinations.
 */

"use client";

import type { DestinationSearchParams } from "@schemas/search";
import { ClockIcon, MapPinIcon, StarIcon, TrendingUpIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import { useMemoryContext } from "@/hooks/use-memory";
import { initTelemetry, withClientTelemetrySpan } from "@/lib/telemetry/client";
import { useSearchForm } from "./common/use-search-form";

/** Zod schema for destination search form values. */
const DestinationSearchFormSchema = z.strictObject({
  language: z.string().optional(),
  limit: z
    .number()
    .int()
    .min(1, { error: "Limit must be at least 1" })
    .max(20, { error: "Limit must be at most 20" }),
  query: z.string().min(1, { error: "Destination is required" }),
  region: z.string().optional(),
  types: z.array(
    z.enum(["locality", "country", "administrative_area", "establishment"])
  ),
});

/** Type for destination search form values. */
export type DestinationSearchFormValues = z.infer<typeof DestinationSearchFormSchema>;

/** Interface for destination suggestions. */
interface DestinationSuggestion {
  placeId: string;
  description: string;
  mainText: string;
  secondaryText: string;
  types: string[];
}

type PlacesApiPlace = {
  id: string;
  displayName?: { text: string };
  formattedAddress?: string;
  types?: string[];
};

/** Interface for destination search form props. */
interface DestinationSearchFormProps {
  onSearch?: (data: DestinationSearchParams) => void;
  initialValues?: Partial<DestinationSearchFormValues>;
  userId?: string;
  showMemoryRecommendations?: boolean;
}

/** Array of destination types. */
const DestinationTypes = [
  {
    description: "Local municipalities and urban areas",
    id: "locality",
    label: "Cities & Towns",
  },
  {
    description: "National territories and regions",
    id: "country",
    label: "Countries",
  },
  {
    description: "Administrative divisions within countries",
    id: "administrative_area",
    label: "States & Regions",
  },
  {
    description: "Notable buildings, monuments, and attractions",
    id: "establishment",
    label: "Landmarks & Places",
  },
];

/** Array of popular destinations. */
const PopularDestinations = [
  "Paris, France",
  "Tokyo, Japan",
  "New York, USA",
  "London, UK",
  "Rome, Italy",
  "Bali, Indonesia",
  "Barcelona, Spain",
  "Dubai, UAE",
];

/**
 * Destination search form with debounced autocomplete and optional
 * memory suggestions.
 *
 * @param onSearch - Callback function to handle search submissions.
 * @param initialValues - Initial values for the form.
 * @param userId - User ID for memory-based recommendations.
 * @param showMemoryRecommendations - Whether to show memory-based recommendations.
 * @returns Destination search form component.
 */
export function DestinationSearchForm({
  onSearch,
  initialValues = {
    limit: 10,
    types: ["locality", "country"],
  },
  userId,
  showMemoryRecommendations = true,
}: DestinationSearchFormProps) {
  const [suggestions, setSuggestions] = useState<DestinationSuggestion[]>([]);

  // Memory-based recommendations
  const { data: memoryContext, isLoading: _memoryLoading } = useMemoryContext(
    userId || "",
    !!userId && showMemoryRecommendations
  );
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const suggestionsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const cacheRef = useRef<Map<string, { places: PlacesApiPlace[]; timestamp: number }>>(
    new Map()
  );
  const { toast } = useToast();
  const CacheTtlMs = 2 * 60_000;

  const form = useSearchForm(
    DestinationSearchFormSchema,
    {
      limit: 10,
      query: "",
      types: ["locality", "country"],
      ...initialValues,
    },
    {}
  );

  useEffect(() => {
    initTelemetry();
  }, []);

  const query = form.watch("query");

  /**
   * Fetches autocomplete suggestions from `/api/places/search` with abort support.
   *
   * @param searchQuery - The query to search for.
   * @returns Promise resolving to an array of destination suggestions.
   * @throws Error if the search fails.
   */
  const fetchAutocompleteSuggestions = useCallback(
    async (searchQuery: string) => {
      const cacheKey = searchQuery.toLowerCase();
      const cached = cacheRef.current.get(cacheKey);
      const limit = form.getValues("limit") ?? 10;
      const selectedTypes = form.getValues("types") ?? [];

      if (cached && Date.now() - cached.timestamp < CacheTtlMs) {
        const filteredCached =
          selectedTypes.length > 0
            ? cached.places.filter((place) =>
                place.types?.some((type) =>
                  selectedTypes.includes(
                    type as DestinationSearchFormValues["types"][number]
                  )
                )
              )
            : cached.places;

        const mappedCached = filteredCached.slice(0, limit).map((place) => ({
          description: place.formattedAddress ?? place.displayName?.text ?? "",
          mainText: place.displayName?.text ?? "Unknown",
          placeId: place.id,
          secondaryText: place.formattedAddress ?? "",
          types: place.types ?? [],
        }));
        setSuggestions(mappedCached);
        setShowSuggestions(true);
        setSuggestionsError(null);
        setIsLoadingSuggestions(false);
        return;
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      setSuggestionsError(null);

      try {
        const requestBody = {
          maxResultCount: limit,
          textQuery: searchQuery,
        };

        const response = await fetch("/api/places/search", {
          body: JSON.stringify(requestBody),
          headers: { "Content-Type": "application/json" },
          method: "POST",
          signal: abortController.signal,
        });

        if (!response.ok) {
          if (response.status === 429) {
            throw new Error("Too many requests. Please try again in a moment.");
          }
          const errorData = (await response.json().catch(() => ({}))) as {
            reason?: string;
          };
          throw new Error(errorData.reason ?? `Search failed: ${response.status}`);
        }

        const data = (await response.json()) as { places?: PlacesApiPlace[] };

        const places = data.places ?? [];
        cacheRef.current.set(cacheKey, { places, timestamp: Date.now() });

        const filteredPlaces =
          selectedTypes.length > 0
            ? places.filter((place) =>
                place.types?.some((type) =>
                  selectedTypes.includes(
                    type as DestinationSearchFormValues["types"][number]
                  )
                )
              )
            : places;

        const mappedSuggestions: DestinationSuggestion[] = filteredPlaces
          .slice(0, limit)
          .map((place) => ({
            description: place.formattedAddress ?? place.displayName?.text ?? "",
            mainText: place.displayName?.text ?? "Unknown",
            placeId: place.id,
            secondaryText: place.formattedAddress ?? "",
            types: place.types ?? [],
          }));

        if (searchQuery !== form.getValues("query")) {
          return;
        }

        setSuggestions(mappedSuggestions);
        setSuggestionsError(null);
        setShowSuggestions(true);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }
        setSuggestionsError(
          error instanceof Error ? error.message : "Unable to fetch suggestions."
        );
        toast({
          description:
            error instanceof Error ? error.message : "Unable to fetch suggestions.",
          title: "Places search failed",
          variant: "destructive",
        });
        setSuggestions([]);
        setShowSuggestions(true);
      } finally {
        setIsLoadingSuggestions(false);
        abortControllerRef.current = null;
      }
    },
    [form, toast]
  );

  // Debounced autocomplete suggestions
  useEffect(() => {
    if (suggestionsTimeoutRef.current) {
      clearTimeout(suggestionsTimeoutRef.current);
    }

    if (query && query.length >= 2) {
      suggestionsTimeoutRef.current = setTimeout(() => {
        setIsLoadingSuggestions(true);
        fetchAutocompleteSuggestions(query);
      }, 300);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
      setIsLoadingSuggestions(false);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    }

    return () => {
      if (suggestionsTimeoutRef.current) {
        clearTimeout(suggestionsTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [fetchAutocompleteSuggestions, query]);

  /** Applies a selected suggestion to the form and hides the dropdown. */
  const handleSuggestionSelect = (suggestion: DestinationSuggestion) => {
    form.setValue("query", suggestion.description);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  /** Prefills the query with a popular destination and focuses the input. */
  const handlePopularDestinationClick = (destination: string) => {
    form.setValue("query", destination);
    inputRef.current?.focus();
  };

  /** Submits the search values to the parent callback. */
  const handleSubmit = (data: DestinationSearchFormValues) =>
    withClientTelemetrySpan(
      "search.destination.form.submit",
      { searchType: "destination" },
      async () => {
        if (onSearch) {
          await onSearch(mapDestinationValuesToParams(data));
        }
      }
    );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Destination Search</CardTitle>
        <CardDescription>
          Discover amazing destinations around the world with intelligent autocomplete
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="query"
                render={({ field: { ref, ...fieldProps } }) => (
                  <FormItem className="relative">
                    <FormLabel>Destination</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          ref={(el) => {
                            ref(el);
                            inputRef.current = el;
                          }}
                          placeholder="Search for cities, countries, or landmarks..."
                          {...fieldProps}
                          autoComplete="off"
                          onFocus={() => {
                            if (suggestions.length > 0) {
                              setShowSuggestions(true);
                            }
                          }}
                          onBlur={() => {
                            // Delay hiding suggestions to allow for clicks
                            setTimeout(() => setShowSuggestions(false), 200);
                          }}
                        />

                        {/* Autocomplete Suggestions Dropdown */}
                        {showSuggestions &&
                          (suggestions.length > 0 ||
                            isLoadingSuggestions ||
                            (!isLoadingSuggestions && (query?.length ?? 0) >= 2)) && (
                            <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                              {isLoadingSuggestions ? (
                                <div className="p-3 text-sm text-gray-500">
                                  Loading suggestions...
                                </div>
                              ) : suggestionsError ? (
                                <div className="p-3 text-sm text-red-600">
                                  {suggestionsError}
                                </div>
                              ) : suggestions.length > 0 ? (
                                suggestions.map((suggestion) => (
                                  <button
                                    key={suggestion.placeId}
                                    type="button"
                                    className="w-full text-left p-3 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none border-b border-gray-100 last:border-b-0"
                                    onClick={() => handleSuggestionSelect(suggestion)}
                                  >
                                    <div className="font-medium text-sm">
                                      {suggestion.mainText}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                      {suggestion.secondaryText}
                                    </div>
                                  </button>
                                ))
                              ) : (
                                <div className="p-3 text-sm text-gray-500">
                                  No suggestions found.
                                </div>
                              )}
                            </div>
                          )}
                      </div>
                    </FormControl>
                    <FormDescription>
                      Start typing to see destination suggestions
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Memory-based Recommendations */}
              {showMemoryRecommendations && memoryContext?.context && (
                <div className="space-y-3">
                  <FormLabel className="text-sm font-medium flex items-center gap-2">
                    <StarIcon className="h-4 w-4 text-yellow-500" />
                    Your Favorite Destinations
                  </FormLabel>
                  <div className="flex flex-wrap gap-2">
                    {memoryContext.context.userPreferences.destinations
                      ?.slice(0, 6)
                      .map((destination) => (
                        <Badge
                          key={destination}
                          variant="outline"
                          className="cursor-pointer hover:bg-yellow-50 hover:border-yellow-300 transition-colors border-yellow-200 text-yellow-700"
                          onClick={() => handlePopularDestinationClick(destination)}
                        >
                          <StarIcon className="h-3 w-3 mr-1" />
                          {destination}
                        </Badge>
                      ))}
                  </div>
                </div>
              )}

              {/* Trending from Travel Patterns */}
              {showMemoryRecommendations &&
                memoryContext?.context?.travelPatterns?.frequentDestinations && (
                  <div className="space-y-3">
                    <FormLabel className="text-sm font-medium flex items-center gap-2">
                      <TrendingUpIcon className="h-4 w-4 text-blue-500" />
                      Your Travel Patterns
                    </FormLabel>
                    <div className="flex flex-wrap gap-2">
                      {memoryContext.context.travelPatterns.frequentDestinations
                        .slice(0, 4)
                        .map((destination) => (
                          <Badge
                            key={destination}
                            variant="outline"
                            className="cursor-pointer hover:bg-blue-50 hover:border-blue-300 transition-colors border-blue-200 text-blue-700"
                            onClick={() => handlePopularDestinationClick(destination)}
                          >
                            <TrendingUpIcon className="h-3 w-3 mr-1" />
                            {destination}
                          </Badge>
                        ))}
                    </div>
                  </div>
                )}

              {/* Recent Memories */}
              {showMemoryRecommendations && memoryContext?.context?.recentMemories && (
                <div className="space-y-3">
                  <FormLabel className="text-sm font-medium flex items-center gap-2">
                    <ClockIcon className="h-4 w-4 text-green-500" />
                    Recent Memories
                  </FormLabel>
                  <div className="flex flex-wrap gap-2">
                    {memoryContext.context.recentMemories
                      .filter(
                        (memory) =>
                          memory.type === "destination" ||
                          memory.content.toLowerCase().includes("visit")
                      )
                      .slice(0, 3)
                      .map((memory) => {
                        // Extract destination names from memory content
                        const matches = memory.content.match(
                          /\b[A-Z][A-Za-z]+(?:[\s-](?:[A-Z][A-Za-z]+|de|da|do|del|los|las|of|the))*\b/g
                        );
                        const destination = matches?.[0] || memory.content.slice(0, 20);
                        return (
                          <Badge
                            key={memory.content}
                            variant="outline"
                            className="cursor-pointer hover:bg-green-50 hover:border-green-300 transition-colors border-green-200 text-green-700"
                            onClick={() => handlePopularDestinationClick(destination)}
                          >
                            <ClockIcon className="h-3 w-3 mr-1" />
                            {destination}
                          </Badge>
                        );
                      })}
                  </div>
                </div>
              )}

              {showMemoryRecommendations && memoryContext?.context && <Separator />}

              {/* Popular Destinations Quick Select */}
              <div className="space-y-3">
                <FormLabel className="text-sm font-medium flex items-center gap-2">
                  <MapPinIcon className="h-4 w-4 text-gray-500" />
                  Popular Destinations
                </FormLabel>
                <div className="flex flex-wrap gap-2">
                  {PopularDestinations.map((destination) => (
                    <Badge
                      key={destination}
                      variant="secondary"
                      className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                      onClick={() => handlePopularDestinationClick(destination)}
                    >
                      {destination}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Destination Types Filter */}
              <FormField
                control={form.control}
                name="types"
                render={() => (
                  <FormItem>
                    <FormLabel>Destination Types</FormLabel>
                    <FormDescription>
                      Select the types of destinations you're interested in
                    </FormDescription>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {DestinationTypes.map((type) => (
                        <label
                          key={type.id}
                          className="flex items-start space-x-3 border rounded-md p-3 cursor-pointer hover:bg-accent transition-colors"
                        >
                          <input
                            type="checkbox"
                            value={type.id}
                            checked={form
                              .watch("types")
                              .includes(
                                type.id as
                                  | "locality"
                                  | "country"
                                  | "administrative_area"
                                  | "establishment"
                              )}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              const types = form.getValues("types");

                              if (checked) {
                                form.setValue("types", [
                                  ...types,
                                  type.id as
                                    | "locality"
                                    | "country"
                                    | "administrative_area"
                                    | "establishment",
                                ]);
                              } else {
                                form.setValue(
                                  "types",
                                  types.filter((t) => t !== type.id)
                                );
                              }
                            }}
                            className="h-4 w-4 mt-0.5"
                          />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{type.label}</div>
                            <div className="text-xs text-gray-500">
                              {type.description}
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Options */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="limit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Results</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          max={20}
                          {...field}
                          onChange={(e) =>
                            field.onChange(Number.parseInt(e.target.value, 10))
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="language"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Language (optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. en, fr, es" {...field} />
                      </FormControl>
                      <FormDescription className="text-xs">
                        ISO language code
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="region"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Region (optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. us, uk, fr" {...field} />
                      </FormControl>
                      <FormDescription className="text-xs">
                        ISO region code
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <Button type="submit" className="w-full">
              Search Destinations
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

// biome-ignore lint/style/useNamingConvention: Utility function name is intentionally camelCase
export function mapDestinationValuesToParams(
  data: DestinationSearchFormValues
): DestinationSearchParams {
  return {
    language: data.language,
    limit: data.limit,
    query: data.query,
    region: data.region,
    types: data.types,
  };
}
