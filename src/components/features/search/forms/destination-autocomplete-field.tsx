/**
 * @fileoverview Autocomplete destination field for the DestinationSearchForm.
 */

"use client";

import type { DestinationSearchFormData } from "@schemas/search";
import type { RefObject } from "react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

type DestinationSuggestion = {
  placeId: string;
  description: string;
  mainText: string;
  secondaryText: string;
  types: string[];
};

type PlacesApiPlace = {
  id: string;
  displayName?: { text: string };
  formattedAddress?: string;
  types?: string[];
};

type DestinationAutocompleteFieldProps = {
  form: UseFormReturn<DestinationSearchFormData>;
  inputRef: RefObject<HTMLInputElement | null>;
};

const CACHE_TTL_MS = 2 * 60_000;
const AUTOCOMPLETE_DEBOUNCE_MS = 300;
const MAX_CACHE_ENTRIES = 50;

function MapPlaceToSuggestion(place: PlacesApiPlace): DestinationSuggestion {
  return {
    description: place.formattedAddress ?? place.displayName?.text ?? "",
    mainText: place.displayName?.text ?? "Unknown",
    placeId: place.id,
    secondaryText: place.formattedAddress ?? "",
    types: place.types ?? [],
  };
}

export function DestinationAutocompleteField({
  form,
  inputRef,
}: DestinationAutocompleteFieldProps) {
  const { toast } = useToast();
  const [suggestions, setSuggestions] = useState<DestinationSuggestion[]>([]);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);

  const suggestionsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const blurTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const cacheRef = useRef<Map<string, { places: PlacesApiPlace[]; timestamp: number }>>(
    new Map()
  );

  const suggestionsListId = useId();
  const query = form.watch("query");

  const filterPlaces = useCallback(
    (places: PlacesApiPlace[]) => {
      const selectedTypes = form.getValues("types") ?? [];
      if (selectedTypes.length === 0) return places;
      const selectedTypeSet = new Set<string>(selectedTypes);
      return places.filter((place) =>
        place.types?.some((type) => selectedTypeSet.has(type))
      );
    },
    [form]
  );

  const fetchAutocompleteSuggestions = useCallback(
    async (searchQuery: string) => {
      const cacheKey = searchQuery.toLowerCase();
      const cached = cacheRef.current.get(cacheKey);
      const limit = form.getValues("limit") ?? 10;

      if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
        cacheRef.current.delete(cacheKey);
        cacheRef.current.set(cacheKey, cached);
        const filteredCached = filterPlaces(cached.places);
        setSuggestions(filteredCached.slice(0, limit).map(MapPlaceToSuggestion));
        setShowSuggestions(true);
        setSuggestionsError(null);
        setIsLoadingSuggestions(false);
        return;
      }

      abortControllerRef.current?.abort();
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
        while (cacheRef.current.size > MAX_CACHE_ENTRIES) {
          const oldestKey = cacheRef.current.keys().next().value;
          if (typeof oldestKey !== "string") break;
          cacheRef.current.delete(oldestKey);
        }

        const filteredPlaces = filterPlaces(places);
        const mappedSuggestions = filteredPlaces
          .slice(0, limit)
          .map(MapPlaceToSuggestion);

        if (searchQuery !== form.getValues("query")) {
          return;
        }

        setSuggestions(mappedSuggestions);
        setSuggestionsError(null);
        setShowSuggestions(true);
        setActiveSuggestionIndex(-1);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }

        const message =
          error instanceof Error ? error.message : "Unable to fetch suggestions.";
        setSuggestionsError(message);
        toast({
          description: message,
          title: "Places search failed",
          variant: "destructive",
        });
        setSuggestions([]);
        setActiveSuggestionIndex(-1);
        setShowSuggestions(true);
      } finally {
        setIsLoadingSuggestions(false);
        abortControllerRef.current = null;
      }
    },
    [filterPlaces, form, toast]
  );

  useEffect(() => {
    if (suggestionsTimeoutRef.current) {
      clearTimeout(suggestionsTimeoutRef.current);
    }

    if (query && query.length >= 2) {
      suggestionsTimeoutRef.current = setTimeout(() => {
        setIsLoadingSuggestions(true);
        fetchAutocompleteSuggestions(query);
      }, AUTOCOMPLETE_DEBOUNCE_MS);
    } else {
      setSuggestions([]);
      setActiveSuggestionIndex(-1);
      setShowSuggestions(false);
      setIsLoadingSuggestions(false);
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
    }

    return () => {
      if (suggestionsTimeoutRef.current) {
        clearTimeout(suggestionsTimeoutRef.current);
      }
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
    };
  }, [fetchAutocompleteSuggestions, query]);

  useEffect(() => {
    return () => {
      if (blurTimeoutRef.current) {
        clearTimeout(blurTimeoutRef.current);
        blurTimeoutRef.current = null;
      }
    };
  }, []);

  const handleSuggestionSelect = useCallback(
    (suggestion: DestinationSuggestion) => {
      form.setValue("query", suggestion.description);
      setShowSuggestions(false);
      setSuggestions([]);
      setActiveSuggestionIndex(-1);
    },
    [form]
  );

  return (
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
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={showSuggestions}
                aria-controls={suggestionsListId}
                aria-activedescendant={
                  activeSuggestionIndex >= 0 && suggestions[activeSuggestionIndex]
                    ? `destination-suggestion-${suggestions[activeSuggestionIndex].placeId}`
                    : undefined
                }
                onKeyDown={(event) => {
                  if (!showSuggestions) return;

                  if (event.key === "Escape") {
                    event.preventDefault();
                    setShowSuggestions(false);
                    setActiveSuggestionIndex(-1);
                    return;
                  }

                  if (suggestions.length === 0) return;

                  if (event.key === "ArrowDown") {
                    event.preventDefault();
                    setActiveSuggestionIndex((prev) =>
                      Math.min(prev + 1, suggestions.length - 1)
                    );
                    return;
                  }

                  if (event.key === "ArrowUp") {
                    event.preventDefault();
                    setActiveSuggestionIndex((prev) => Math.max(prev - 1, 0));
                    return;
                  }

                  if (event.key === "Enter" && activeSuggestionIndex >= 0) {
                    event.preventDefault();
                    const suggestion = suggestions[activeSuggestionIndex];
                    if (suggestion) handleSuggestionSelect(suggestion);
                  }
                }}
                onFocus={() => {
                  if (blurTimeoutRef.current) {
                    clearTimeout(blurTimeoutRef.current);
                    blurTimeoutRef.current = null;
                  }
                  if (suggestions.length > 0) {
                    setShowSuggestions(true);
                  }
                }}
                onBlur={() => {
                  if (blurTimeoutRef.current) {
                    clearTimeout(blurTimeoutRef.current);
                  }
                  blurTimeoutRef.current = setTimeout(() => {
                    setShowSuggestions(false);
                    setActiveSuggestionIndex(-1);
                  }, 200);
                }}
              />

              {showSuggestions &&
                (suggestions.length > 0 ||
                  isLoadingSuggestions ||
                  (query?.length ?? 0) >= 2) && (
                  <div
                    id={suggestionsListId}
                    role="listbox"
                    className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto"
                  >
                    {isLoadingSuggestions ? (
                      <div className="p-3 text-sm text-gray-500">
                        Loading suggestions...
                      </div>
                    ) : suggestionsError ? (
                      <div className="p-3 text-sm text-red-600">{suggestionsError}</div>
                    ) : suggestions.length > 0 ? (
                      suggestions.map((suggestion, index) => (
                        <div
                          key={suggestion.placeId}
                          aria-label={suggestion.mainText}
                          role="option"
                          id={`destination-suggestion-${suggestion.placeId}`}
                          aria-selected={activeSuggestionIndex === index}
                          className="w-full text-left p-3 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none border-b border-gray-100 last:border-b-0 data-[active=true]:bg-gray-50"
                          tabIndex={-1}
                          onMouseDown={(event) => {
                            event.preventDefault();
                            handleSuggestionSelect(suggestion);
                          }}
                          onMouseEnter={() => {
                            setActiveSuggestionIndex(index);
                          }}
                          data-active={activeSuggestionIndex === index}
                        >
                          <div className="font-medium text-sm">
                            {suggestion.mainText}
                          </div>
                          <div className="text-xs text-gray-500">
                            {suggestion.secondaryText}
                          </div>
                        </div>
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
          <FormDescription>Start typing to see destination suggestions</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
