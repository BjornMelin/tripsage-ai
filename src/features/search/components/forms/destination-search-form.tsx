/**
 * @fileoverview Destination search form component for searching destinations.
 */

"use client";

import {
  type DestinationSearchFormData,
  type DestinationSearchParams,
  destinationSearchFormSchema,
  destinationSearchParamsSchema,
} from "@schemas/search";
import { ClockIcon, StarIcon, TrendingUpIcon } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useSearchHistoryStore } from "@/features/search/store/search-history";
import { useMemoryContext } from "@/hooks/use-memory";
import { initTelemetry } from "@/lib/telemetry/client";
import { buildRecentQuickSelectItems } from "../common/recent-items";
import { type QuickSelectItem, SearchFormShell } from "../common/search-form-shell";
import { useSearchForm } from "../common/use-search-form";
import { DestinationAutocompleteField } from "./destination-autocomplete-field";

/** Type for destination search form values. */
export type DestinationSearchFormValues = DestinationSearchFormData;

/** Interface for destination search form props. */
interface DestinationSearchFormProps {
  onSearch?: (data: DestinationSearchParams) => void | Promise<void>;
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
  // Memory-based recommendations
  const { data: memoryContext, isLoading: _memoryLoading } = useMemoryContext(
    userId || "",
    !!userId && showMemoryRecommendations
  );
  const inputRef = useRef<HTMLInputElement>(null);

  const form = useSearchForm(
    destinationSearchFormSchema,
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

  const watchedTypes = form.watch("types");
  const watchedLimit = form.watch("limit");

  const recentSearchesByType = useSearchHistoryStore(
    (state) => state.recentSearchesByType.destination
  );
  const recentSearches = useMemo(
    () => recentSearchesByType.slice(0, 4),
    [recentSearchesByType]
  );

  const defaultLimit = watchedLimit ?? 10;
  const defaultTypes = watchedTypes ?? ["locality", "country"];

  const recentItems: QuickSelectItem<DestinationSearchFormValues>[] = useMemo(() => {
    return buildRecentQuickSelectItems<
      DestinationSearchFormValues,
      DestinationSearchParams
    >(recentSearches, destinationSearchParamsSchema, (params, search) => {
      const description = params.types?.join(", ");

      const item: QuickSelectItem<DestinationSearchFormValues> = {
        id: search.id,
        label: params.query,
        params: {
          language: params.language,
          limit: params.limit ?? defaultLimit,
          query: params.query,
          region: params.region,
          types: params.types ?? defaultTypes,
        },
        ...(description ? { description } : {}),
      };

      return item;
    });
  }, [defaultLimit, defaultTypes, recentSearches]);

  const popularItems: QuickSelectItem<DestinationSearchFormValues>[] = useMemo(() => {
    return PopularDestinations.map((destination) => ({
      id: destination,
      label: destination,
      params: { query: destination },
    }));
  }, []);

  const handleQuickSelectDestination = (
    values: Partial<DestinationSearchFormValues>
  ) => {
    if (values.query !== undefined) {
      form.setValue("query", values.query, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });
    }

    if (values.types !== undefined) {
      form.setValue("types", values.types, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });
    }

    if (values.limit !== undefined) {
      form.setValue("limit", values.limit, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });
    }

    if (values.language !== undefined) {
      form.setValue("language", values.language, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });
    }

    if (values.region !== undefined) {
      form.setValue("region", values.region, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });
    }

    inputRef.current?.focus();
  };

  const handleSubmit = async (data: DestinationSearchFormValues) => {
    if (onSearch) {
      await onSearch(mapDestinationValuesToParams(data));
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
        <SearchFormShell
          form={form}
          onSubmit={handleSubmit}
          telemetrySpanName="search.destination.form.submit"
          telemetryAttributes={{ searchType: "destination" }}
          telemetryErrorMetadata={{
            action: "submit",
            context: "DestinationSearchForm",
          }}
          submitLabel="Search Destinations"
          loadingLabel="Searching destinations…"
          className="space-y-6"
          popularItems={popularItems}
          popularLabel="Popular Destinations"
          onPopularItemSelect={(item) => handleQuickSelectDestination(item.params)}
          recentItems={recentItems}
          recentLabel="Recent searches"
          onRecentItemSelect={(item) => handleQuickSelectDestination(item.params)}
        >
          {(renderForm) => (
            <div className="space-y-4">
              <DestinationAutocompleteField form={renderForm} inputRef={inputRef} />

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
                          onClick={() =>
                            handleQuickSelectDestination({ query: destination })
                          }
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
                            onClick={() =>
                              handleQuickSelectDestination({ query: destination })
                            }
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
                            onClick={() =>
                              handleQuickSelectDestination({ query: destination })
                            }
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
                            checked={watchedTypes.includes(
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
                                form.setValue(
                                  "types",
                                  [
                                    ...types,
                                    type.id as
                                      | "locality"
                                      | "country"
                                      | "administrative_area"
                                      | "establishment",
                                  ],
                                  { shouldDirty: true, shouldValidate: true }
                                );
                              } else {
                                form.setValue(
                                  "types",
                                  types.filter((t) => t !== type.id),
                                  { shouldDirty: true, shouldValidate: true }
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
          )}
        </SearchFormShell>
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
