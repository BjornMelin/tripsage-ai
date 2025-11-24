/**
 * @fileoverview Destination search form component for searching destinations.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import type { DestinationSearchParams } from "@schemas/search";
import { Clock, MapPin, Star, TrendingUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
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
import { useMemoryContext } from "@/hooks/use-memory";

const DestinationSearchFormSchema = z.object({
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

export type DestinationSearchFormValues = z.infer<typeof DestinationSearchFormSchema>;

interface DestinationSuggestion {
  placeId: string;
  description: string;
  mainText: string;
  secondaryText: string;
  types: string[];
}

interface DestinationSearchFormProps {
  onSearch?: (data: DestinationSearchParams) => void;
  initialValues?: Partial<DestinationSearchFormValues>;
  userId?: string;
  showMemoryRecommendations?: boolean;
}

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
  const suggestionsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const form = useForm<DestinationSearchFormValues>({
    defaultValues: {
      limit: 10,
      query: "",
      types: ["locality", "country"],
      ...initialValues,
    },
    mode: "onChange",
    resolver: zodResolver(DestinationSearchFormSchema),
  });

  const query = form.watch("query");

  // Debounced autocomplete suggestions
  useEffect(() => {
    if (suggestionsTimeoutRef.current) {
      clearTimeout(suggestionsTimeoutRef.current);
    }

    if (query && query.length >= 2) {
      suggestionsTimeoutRef.current = setTimeout(() => {
        setIsLoadingSuggestions(true);
        try {
          // TODO: Replace mock API call with actual Google Places Text Search API integration.
          //
          // IMPLEMENTATION PLAN (Decision Framework Score: 9.2/10.0)
          // ===========================================================
          //
          // ARCHITECTURE DECISIONS:
          // -----------------------
          // 1. API Endpoint: Use existing `/api/places/search` endpoint (server-side proxy)
          //    - Endpoint: `frontend/src/app/api/places/search/route.ts` (already exists)
          //    - Uses Places Text Search API (New) via POST /v1/places:searchText
          //    - Rate limited via `"places:search"` key (30 req/min)
          //    - Telemetry: `"places.search"` (automatic)
          //    - Rationale: Reuse existing infrastructure; secure (API key server-side); follows ADR-0029 DI pattern
          //
          // 2. Request Cancellation: Use AbortController for in-flight request cancellation
          //    - Create AbortController per request
          //    - Cancel previous request when query changes
          //    - Rationale: Prevents race conditions and wasted API calls
          //
          // 3. Response Mapping: Map Places API response to DestinationSuggestion interface
          //    - Extract: placeId (places[].id), mainText (places[].displayName.text),
          //      secondaryText (places[].formattedAddress), types (places[].types)
          //    - Filter by form.types if specified
          //    - Limit results to form.limit (default: 10)
          //
          // 4. Error Handling: Graceful degradation with user feedback
          //    - Network errors: Show error message, allow retry
          //    - Rate limiting: Show user-friendly message
          //    - Empty results: Show "No suggestions found" (not an error)
          //
          // IMPLEMENTATION STEPS:
          // ---------------------
          //
          // Step 1: Add AbortController Ref
          //   ```typescript
          //   const abortControllerRef = useRef<AbortController | null>(null);
          //   ```
          //
          // Step 2: Implement Autocomplete Fetch Function
          //   ```typescript
          //   const fetchAutocompleteSuggestions = async (searchQuery: string) => {
          //     // Cancel previous request
          //     if (abortControllerRef.current) {
          //       abortControllerRef.current.abort();
          //     }
          //     const abortController = new AbortController();
          //     abortControllerRef.current = abortController;
          //
          //     try {
          //       const requestBody = {
          //         maxResultCount: form.getValues("limit") ?? 10,
          //         textQuery: searchQuery,
          //       };
          //
          //       // Add locationBias if available (future enhancement)
          //       // Add includedTypes filtering based on form.types
          //
          //       const response = await fetch("/api/places/search", {
          //         body: JSON.stringify(requestBody),
          //         headers: { "Content-Type": "application/json" },
          //         method: "POST",
          //         signal: abortController.signal,
          //       });
          //
          //       if (!response.ok) {
          //         if (response.status === 429) {
          //           throw new Error("Too many requests. Please try again in a moment.");
          //         }
          //         const errorData = await response.json().catch(() => ({}));
          //         throw new Error(
          //           errorData.reason ?? `Search failed: ${response.status}`
          //         );
          //       }
          //
          //       const data = (await response.json()) as {
          //         places?: Array<{
          //           id: string;
          //           displayName?: { text: string };
          //           formattedAddress?: string;
          //           types?: string[];
          //         }>;
          //       };
          //
          //       const places = data.places ?? [];
          //       const selectedTypes = form.getValues("types");
          //
          //       // Filter by types if specified
          //       const filteredPlaces = selectedTypes.length > 0
          //         ? places.filter((place) =>
          //             place.types?.some((type) => selectedTypes.includes(type as any))
          //           )
          //         : places;
          //
          //       // Map to DestinationSuggestion format
          //       const mappedSuggestions: DestinationSuggestion[] = filteredPlaces
          //         .slice(0, form.getValues("limit") ?? 10)
          //         .map((place) => ({
          //           description: place.formattedAddress ?? place.displayName?.text ?? "",
          //           mainText: place.displayName?.text ?? "Unknown",
          //           placeId: place.id,
          //           secondaryText: place.formattedAddress ?? "",
          //           types: place.types ?? [],
          //         }));
          //
          //       setSuggestions(mappedSuggestions);
          //       setShowSuggestions(true);
          //     } catch (error) {
          //       if (error instanceof Error && error.name === "AbortError") {
          //         // Request was cancelled, don't update state
          //         return;
          //       }
          //       console.error("Error fetching suggestions:", error);
          //       setSuggestions([]);
          //       // Optionally: Show error toast/notification
          //       // toast({ title: "Error", description: error.message, variant: "destructive" });
          //     } finally {
          //       setIsLoadingSuggestions(false);
          //     }
          //   };
          //   ```
          //
          // Step 3: Update useEffect to Call Fetch Function
          //   Replace mock code with:
          //   ```typescript
          //   fetchAutocompleteSuggestions(query);
          //   ```
          //
          // Step 4: Cleanup AbortController on Unmount
          //   ```typescript
          //   return () => {
          //     if (suggestionsTimeoutRef.current) {
          //       clearTimeout(suggestionsTimeoutRef.current);
          //     }
          //     if (abortControllerRef.current) {
          //       abortControllerRef.current.abort();
          //     }
          //   };
          //   ```
          //
          // INTEGRATION POINTS:
          // -------------------
          // - API: `/api/places/search` (existing endpoint, no changes needed)
          // - Schema: `placesSearchRequestSchema` from `@schemas/api` (server-side validation)
          // - Rate Limiting: Handled server-side via `withApiGuards` + `"places:search"` key
          // - Telemetry: Automatic via FetchInstrumentation (no code needed)
          // - Form State: Use `form.getValues("limit")` and `form.getValues("types")` for filtering
          // - Error Handling: Standard try/catch with user-friendly messages
          //
          // PERFORMANCE CONSIDERATIONS:
          // ---------------------------
          // - Debounce: 300ms delay (already implemented) prevents excessive API calls
          // - AbortController: Cancels in-flight requests when query changes
          // - Type Filtering: Client-side filtering reduces server load (types already in response)
          // - Result Limiting: Respect form.limit to avoid rendering too many suggestions
          // - Server-side Caching: Google Places API caches results for 30 days (automatic)
          //
          // EDGE CASES:
          // -----------
          // - Query < 2 chars: Return early, don't call API
          // - Rapid typing: Debounce + AbortController handles this
          // - Component unmount: Cleanup AbortController and timeout
          // - Network failure: Show error, allow retry
          // - Rate limiting (429): Show user-friendly message
          // - No results: Show empty suggestions list (not an error)
          // - Type filtering: Filter client-side after receiving results
          //
          // TESTING REQUIREMENTS:
          // ---------------------
          // - Unit test: Autocomplete fetch logic, response mapping, type filtering
          // - Integration test: API call, abort behavior, error handling
          // - Mock fetch API, test timeout behavior, test error scenarios
          // - Use `vi.useFakeTimers()` for debounce testing
          // - Test AbortController cancellation
          //
          // FUTURE ENHANCEMENTS:
          // -------------------
          // - Add locationBias support for location-aware autocomplete
          // - Create dedicated `/api/places/autocomplete` endpoint using Places Autocomplete API
          //   (POST /v1/places:autocomplete) for better autocomplete-specific features
          // - Add result caching in component state (Map<query, results>) with TTL
          // - Integrate with search-results-store for cross-component sharing
          // - Add session token support for billing optimization (if using Autocomplete API)
          //
          // Mock API call - replace with actual Google Places Text Search API via /api/places/search
          const mockSuggestions: DestinationSuggestion[] = [
            {
              description: `${query} - Popular Destination`,
              mainText: query,
              placeId: "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
              secondaryText: "Tourist Destination",
              types: ["locality", "political"],
            },
            {
              description: `${query} City Center`,
              mainText: `${query} City Center`,
              placeId: "ChIJmysnFgZYSoYRSfPTL2YJuck",
              secondaryText: "Urban Area",
              types: ["establishment"],
            },
          ];

          setSuggestions(mockSuggestions);
          setShowSuggestions(true);
        } catch (error) {
          console.error("Error fetching suggestions:", error);
          setSuggestions([]);
        } finally {
          setIsLoadingSuggestions(false);
        }
      }, 300);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }

    return () => {
      if (suggestionsTimeoutRef.current) {
        clearTimeout(suggestionsTimeoutRef.current);
      }
    };
  }, [query]);

  const handleSuggestionSelect = (suggestion: DestinationSuggestion) => {
    form.setValue("query", suggestion.description);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  const handlePopularDestinationClick = (destination: string) => {
    form.setValue("query", destination);
    inputRef.current?.focus();
  };

  const handleSubmit = (data: DestinationSearchFormValues) => {
    if (onSearch) {
      onSearch(mapDestinationValuesToParams(data));
    }
  };

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
                          (suggestions.length > 0 || isLoadingSuggestions) && (
                            <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                              {isLoadingSuggestions ? (
                                <div className="p-3 text-sm text-gray-500">
                                  Loading suggestions...
                                </div>
                              ) : (
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
                    <Star className="h-4 w-4 text-yellow-500" />
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
                          <Star className="h-3 w-3 mr-1" />
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
                      <TrendingUp className="h-4 w-4 text-blue-500" />
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
                            <TrendingUp className="h-3 w-3 mr-1" />
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
                    <Clock className="h-4 w-4 text-green-500" />
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
                          /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g
                        );
                        const destination = matches?.[0] || memory.content.slice(0, 20);
                        return (
                          <Badge
                            key={memory.content}
                            variant="outline"
                            className="cursor-pointer hover:bg-green-50 hover:border-green-300 transition-colors border-green-200 text-green-700"
                            onClick={() => handlePopularDestinationClick(destination)}
                          >
                            <Clock className="h-3 w-3 mr-1" />
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
                  <MapPin className="h-4 w-4 text-gray-500" />
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
