/**
 * @fileoverview General-purpose debounced search hook.
 */

import { useCallback, useEffect, useRef, useState } from "react";

/** Interface defining the return type of the useSearch hook. */
export interface UseSearchResult {
  search: (query: string) => Promise<void>;
  isSearching: boolean;
  results: unknown[];
  error: Error | null;
  clearSearch: () => void;
}

/**
 * Hook for general-purpose debounced search functionality.
 *
 * Provides methods for searching, managing search state, and clearing search results.
 *
 * @returns Object with search methods and state
 */
export function useSearch(): UseSearchResult {
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<unknown[]>([]);
  const [error, setError] = useState<Error | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Performs the actual search operation.
   *
   * @param query - The search query to perform.
   */
  const performSearch = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setResults([]);
      setError(null);
      setIsSearching(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsSearching(true);
    setError(null);

    try {
      const response = await fetch("/api/search", {
        body: JSON.stringify({ query: trimmed }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
        signal: abortController.signal,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.reason ?? `Search failed with status ${response.status}`);
      }

      const data = (await response.json()) as { results?: unknown[] };
      setResults(data.results ?? []);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      const normalized = err instanceof Error ? err : new Error(String(err));
      setError(normalized);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const search = useCallback(
    (query: string): Promise<void> =>
      new Promise((resolve, reject) => {
        if (debounceTimeoutRef.current) {
          clearTimeout(debounceTimeoutRef.current);
        }

        debounceTimeoutRef.current = setTimeout(async () => {
          try {
            await performSearch(query);
            resolve();
          } catch (err) {
            reject(err);
          }
        }, 300);
      }),
    [performSearch]
  );

  /** Clears the current search state. */
  const clearSearch = useCallback(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
      debounceTimeoutRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsSearching(false);
    setError(null);
    setResults([]);
  }, []);

  /** Cleans up the search state on unmount. */
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  /** Returns the search methods and state. */
  return {
    clearSearch,
    error,
    isSearching,
    results,
    search,
  };
}
