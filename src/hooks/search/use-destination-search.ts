/**
 * @fileoverview Destination search hook backed by the Places Text Search API.
 */

import type { PlacesSearchRequest } from "@schemas/api";
import type { Destination } from "@schemas/search";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchResultsStore } from "@/stores/search-results-store";

export interface DestinationSearchParams {
  query: string;
  types?: string[];
  limit?: number;
}

export interface DestinationResult {
  placeId: string;
  name: string;
  address: string;
  location?: { lat: number; lng: number };
  types: string[];
}

export interface UseDestinationSearchResult {
  searchDestinations: (
    params: DestinationSearchParams,
    signal?: AbortSignal
  ) => Promise<void>;
  isSearching: boolean;
  searchError: Error | null;
  resetSearch: () => void;
  results: DestinationResult[];
}

interface PlacesSearchResponse {
  places?: Array<{
    id: string;
    displayName?: { text: string };
    formattedAddress?: string;
    location?: { latitude: number; longitude: number };
    types?: string[];
  }>;
}

function normalizeLimit(limit?: number): number {
  const DefaultLimit = 10;
  if (typeof limit !== "number" || Number.isNaN(limit)) {
    return DefaultLimit;
  }
  const clamped = Math.min(Math.max(Math.trunc(limit), 1), 20);
  return clamped;
}

/**
 * Hook for destination search functionality.
 *
 * @returns Object with search methods and state
 */
export function useDestinationSearch(): UseDestinationSearchResult {
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<Error | null>(null);
  const [results, setResults] = useState<DestinationResult[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentSearchIdRef = useRef<string | null>(null);

  const {
    startSearch,
    setSearchResults,
    setSearchError: setStoreSearchError,
    cancelSearch,
  } = useSearchResultsStore();

  const toDestination = useCallback((result: DestinationResult): Destination | null => {
    if (!result.location) {
      return null;
    }

    return {
      attractions: [],
      bestTimeToVisit: undefined,
      climate: undefined,
      coordinates: {
        lat: result.location.lat,
        lng: result.location.lng,
      },
      country: undefined,
      description: result.address || result.name,
      formattedAddress: result.address || result.name,
      id: result.placeId,
      name: result.name,
      photos: undefined,
      placeId: result.placeId,
      popularityScore: undefined,
      rating: undefined,
      region: undefined,
      types: result.types,
    };
  }, []);

  const performSearch = useCallback(
    async (params: DestinationSearchParams, externalSignal?: AbortSignal) => {
      const trimmedQuery = params.query?.trim() ?? "";

      if (trimmedQuery.length < 2) {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }

        if (currentSearchIdRef.current) {
          cancelSearch(currentSearchIdRef.current);
          currentSearchIdRef.current = null;
        }

        setResults([]);
        setSearchError(null);
        setIsSearching(false);
        return;
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      externalSignal?.addEventListener("abort", () => abortController.abort(), {
        once: true,
      });

      setIsSearching(true);
      setSearchError(null);

      const maxResultCount = normalizeLimit(params.limit);

      const searchId = startSearch("destination", {
        limit: maxResultCount,
        query: trimmedQuery,
        types: params.types,
      });
      currentSearchIdRef.current = searchId;

      try {
        const requestBody: PlacesSearchRequest = {
          maxResultCount,
          textQuery: trimmedQuery,
        };

        const response = await fetch("/api/places/search", {
          body: JSON.stringify(requestBody),
          headers: { "Content-Type": "application/json" },
          method: "POST",
          signal: abortController.signal,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.reason ?? `Search failed with status ${response.status}`
          );
        }

        const data = (await response.json()) as PlacesSearchResponse;
        const places = data.places ?? [];

        const mappedResults: DestinationResult[] = places
          .filter((place) => {
            if (params.types && params.types.length > 0) {
              return place.types?.some((type) => params.types?.includes(type));
            }
            return true;
          })
          .slice(0, maxResultCount)
          .map((place) => ({
            address: place.formattedAddress ?? "",
            location:
              place.location?.latitude !== undefined &&
              place.location?.longitude !== undefined
                ? {
                    lat: place.location.latitude,
                    lng: place.location.longitude,
                  }
                : undefined,
            name: place.displayName?.text ?? "Unknown Destination",
            placeId: place.id,
            types: place.types ?? [],
          }));

        setResults(mappedResults);

        const destinations = mappedResults
          .map(toDestination)
          .filter((item): item is Destination => item !== null)
          .slice(0, maxResultCount);

        if (destinations.length > 0) {
          setSearchResults(searchId, { destinations });
        }

        setSearchError(null);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          if (currentSearchIdRef.current) {
            cancelSearch(currentSearchIdRef.current);
            currentSearchIdRef.current = null;
          }
          return;
        }
        const err = error instanceof Error ? error : new Error(String(error));
        setSearchError(err);
        setResults([]);
        if (currentSearchIdRef.current) {
          setStoreSearchError(currentSearchIdRef.current, {
            code: "DESTINATION_SEARCH_ERROR",
            message: err.message,
            occurredAt: new Date().toISOString(),
            retryable: true,
          });
        }
      } finally {
        setIsSearching(false);
      }
    },
    [cancelSearch, setSearchResults, setStoreSearchError, startSearch, toDestination]
  );

  const debounceState = useRef<{
    abortHandler?: () => void;
    abortSignal?: AbortSignal;
    timeoutId: ReturnType<typeof setTimeout> | null;
    reject?: (reason?: unknown) => void;
  }>({
    timeoutId: null,
  });

  const debouncedSearch = useCallback(
    (params: DestinationSearchParams, externalSignal?: AbortSignal): Promise<void> =>
      new Promise<void>((resolve, reject) => {
        if (externalSignal?.aborted) {
          const abortError = new Error("Aborted");
          abortError.name = "AbortError";
          reject(abortError);
          return;
        }
        const state = debounceState.current;
        if (state.timeoutId) {
          clearTimeout(state.timeoutId);
          const abortError = new Error("Debounced");
          abortError.name = "AbortError";
          state.reject?.(abortError);
          if (state.abortSignal && state.abortHandler) {
            state.abortSignal.removeEventListener("abort", state.abortHandler);
          }
        }

        const abortHandler = () => {
          const current = debounceState.current;
          if (current.timeoutId) {
            clearTimeout(current.timeoutId);
            current.timeoutId = null;
            const abortError = new Error("Aborted");
            abortError.name = "AbortError";
            reject(abortError);
            current.reject = undefined;
          }
        };

        externalSignal?.addEventListener("abort", abortHandler, { once: true });
        const timeoutId = setTimeout(async () => {
          debounceState.current.timeoutId = null;
          debounceState.current.reject = undefined;
          if (debounceState.current.abortSignal && debounceState.current.abortHandler) {
            debounceState.current.abortSignal.removeEventListener(
              "abort",
              debounceState.current.abortHandler
            );
          }
          debounceState.current.abortSignal = undefined;
          debounceState.current.abortHandler = undefined;
          try {
            await performSearch(params, externalSignal);
            resolve();
          } catch (error) {
            reject(error);
          }
        }, 300);

        debounceState.current = {
          abortHandler,
          abortSignal: externalSignal,
          reject,
          timeoutId,
        };
      }),
    [performSearch]
  );

  const searchDestinations = useCallback(
    (params: DestinationSearchParams, externalSignal?: AbortSignal): Promise<void> =>
      debouncedSearch(params, externalSignal),
    [debouncedSearch]
  );

  const resetSearch = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (debounceState.current.timeoutId) {
      clearTimeout(debounceState.current.timeoutId);
      debounceState.current.timeoutId = null;
      const abortError = new Error("Reset");
      abortError.name = "AbortError";
      debounceState.current.reject?.(abortError);
      debounceState.current.reject = undefined;
    }
    if (debounceState.current.abortSignal && debounceState.current.abortHandler) {
      debounceState.current.abortSignal.removeEventListener(
        "abort",
        debounceState.current.abortHandler
      );
    }
    debounceState.current.abortSignal = undefined;
    debounceState.current.abortHandler = undefined;
    setIsSearching(false);
    setSearchError(null);
    setResults([]);
  }, []);

  useEffect(
    () => () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      if (debounceState.current.timeoutId) {
        clearTimeout(debounceState.current.timeoutId);
        debounceState.current.timeoutId = null;
        const abortError = new Error("Unmount");
        abortError.name = "AbortError";
        debounceState.current.reject?.(abortError);
        debounceState.current.reject = undefined;
      }
      if (debounceState.current.abortSignal && debounceState.current.abortHandler) {
        debounceState.current.abortSignal.removeEventListener(
          "abort",
          debounceState.current.abortHandler
        );
      }
      debounceState.current.abortSignal = undefined;
      debounceState.current.abortHandler = undefined;
    },
    []
  );

  return {
    isSearching,
    resetSearch,
    results,
    searchDestinations,
    searchError,
  };
}
