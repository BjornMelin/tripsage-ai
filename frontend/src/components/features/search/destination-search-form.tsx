"use client";

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
import type { DestinationSearchParams } from "@/types/search";
import { zodResolver } from "@hookform/resolvers/zod";
import { Clock, MapPin, Star, TrendingUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

const destinationSearchFormSchema = z.object({
  query: z.string().min(1, { message: "Destination is required" }),
  types: z.array(
    z.enum(["locality", "country", "administrative_area", "establishment"])
  ),
  language: z.string().optional(),
  region: z.string().optional(),
  limit: z.number().min(1).max(20),
});

type DestinationSearchFormValues = z.infer<typeof destinationSearchFormSchema>;

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

const DESTINATION_TYPES = [
  {
    id: "locality",
    label: "Cities & Towns",
    description: "Local municipalities and urban areas",
  },
  {
    id: "country",
    label: "Countries",
    description: "National territories and regions",
  },
  {
    id: "administrative_area",
    label: "States & Regions",
    description: "Administrative divisions within countries",
  },
  {
    id: "establishment",
    label: "Landmarks & Places",
    description: "Notable buildings, monuments, and attractions",
  },
];

const POPULAR_DESTINATIONS = [
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
    types: ["locality", "country"],
    limit: 10,
  },
  userId,
  showMemoryRecommendations = true,
}: DestinationSearchFormProps) {
  const [suggestions, setSuggestions] = useState<DestinationSuggestion[]>([]);

  // Memory-based recommendations
  const { data: memoryContext, isLoading: memoryLoading } = useMemoryContext(
    userId || "",
    !!userId && showMemoryRecommendations
  );
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const suggestionsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const form = useForm<DestinationSearchFormValues>({
    resolver: zodResolver(destinationSearchFormSchema),
    defaultValues: {
      query: "",
      types: ["locality", "country"],
      limit: 10,
      ...initialValues,
    },
    mode: "onChange",
  });

  const query = form.watch("query");

  // Debounced autocomplete suggestions
  useEffect(() => {
    if (suggestionsTimeoutRef.current) {
      clearTimeout(suggestionsTimeoutRef.current);
    }

    if (query && query.length >= 2) {
      suggestionsTimeoutRef.current = setTimeout(async () => {
        setIsLoadingSuggestions(true);
        try {
          // Mock API call - replace with actual Google Places Autocomplete API
          const mockSuggestions: DestinationSuggestion[] = [
            {
              placeId: "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
              description: `${query} - Popular Destination`,
              mainText: query,
              secondaryText: "Tourist Destination",
              types: ["locality", "political"],
            },
            {
              placeId: "ChIJmysnFgZYSoYRSfPTL2YJuck",
              description: `${query} City Center`,
              mainText: `${query} City Center`,
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

  function onSubmit(data: DestinationSearchFormValues) {
    const searchParams: DestinationSearchParams = {
      query: data.query,
      types: data.types,
      language: data.language,
      region: data.region,
      limit: data.limit,
    };

    console.log("Destination search params:", searchParams);

    if (onSearch) {
      onSearch(searchParams);
    }
  }

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
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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
                      .map((destination, idx) => (
                        <Badge
                          key={idx}
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
                        .map((destination, idx) => (
                          <Badge
                            key={idx}
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
                      .map((memory, idx) => {
                        // Extract destination names from memory content
                        const matches = memory.content.match(
                          /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g
                        );
                        const destination = matches?.[0] || memory.content.slice(0, 20);
                        return (
                          <Badge
                            key={idx}
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
                  {POPULAR_DESTINATIONS.map((destination) => (
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
                      {DESTINATION_TYPES.map((type) => (
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

              {/* Advanced Options */}
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
                            field.onChange(Number.parseInt(e.target.value))
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
