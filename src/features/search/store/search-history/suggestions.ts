/**
 * @fileoverview Search suggestions slice for search history store.
 */

import type { StateCreator } from "zustand";
import { getCurrentTimestamp } from "@/features/shared/store/helpers";
import type { SearchHistoryState, SearchSuggestion, SuggestionsSlice } from "./types";

/**
 * Extracts meaningful search text from search parameters.
 */
const extractSearchText = (params: Record<string, unknown>): string => {
  const textFields = ["origin", "destination", "query", "location", "name"];

  for (const field of textFields) {
    if (params[field] && typeof params[field] === "string") {
      return params[field] as string;
    }
  }

  return "";
};

export const createSuggestionsSlice: StateCreator<
  SearchHistoryState,
  [],
  [],
  SuggestionsSlice
> = (set, get) => ({
  addSearchTerm: (term, searchType) => {
    set((state) => {
      const existingIndex = state.popularSearchTerms.findIndex(
        (t) => t.term === term && t.searchType === searchType
      );

      if (existingIndex >= 0) {
        const updatedTerms = [...state.popularSearchTerms];
        updatedTerms[existingIndex].count += 1;
        return { popularSearchTerms: updatedTerms };
      }
      return {
        popularSearchTerms: [
          ...state.popularSearchTerms,
          { count: 1, searchType, term },
        ].slice(0, 200), // Keep top 200 terms
      };
    });
  },

  getSearchSuggestions: (query, searchType, limit = 10) => {
    const { searchSuggestions } = get();
    let filtered = searchSuggestions;

    if (query) {
      filtered = searchSuggestions.filter((suggestion) =>
        suggestion.text.toLowerCase().includes(query.toLowerCase())
      );
    }

    if (searchType) {
      filtered = filtered.filter((suggestion) => suggestion.searchType === searchType);
    }

    return filtered
      .sort((a, b) => {
        // Sort by frequency and recency
        const frequencyScore = b.frequency - a.frequency;
        const recencyScore =
          new Date(b.lastUsed).getTime() - new Date(a.lastUsed).getTime();
        return frequencyScore * 0.7 + recencyScore * 0.3;
      })
      .slice(0, limit);
  },
  popularSearchTerms: [],
  searchSuggestions: [],

  updateSearchSuggestions: () => {
    const { recentSearches, savedSearches, popularSearchTerms } = get();
    const MaxSuggestions = 50;
    const seen = new Map<string, SearchSuggestion>();

    // Helper to add suggestion with deduplication
    const addSuggestion = (suggestion: SearchSuggestion): boolean => {
      if (seen.size >= MaxSuggestions) return false;
      const key = `${suggestion.text.toLowerCase()}_${suggestion.searchType}`;
      const existing = seen.get(key);
      if (!existing || existing.frequency < suggestion.frequency) {
        seen.set(key, suggestion);
      }
      return true;
    };

    // Process recent searches (limit to 50 most recent)
    for (const search of recentSearches.slice(0, 50)) {
      const text = extractSearchText(search.params);
      if (text) {
        addSuggestion({
          frequency: 1,
          id: `recent_${search.id}`,
          lastUsed: search.timestamp,
          searchType: search.searchType,
          source: "history",
          text,
        });
      }
    }

    // Process saved searches (limit to 20)
    for (const search of savedSearches.slice(0, 20)) {
      const text = extractSearchText(search.params);
      if (text) {
        addSuggestion({
          frequency: search.usageCount,
          id: `saved_${search.id}`,
          lastUsed: search.lastUsed || search.createdAt,
          searchType: search.searchType,
          source: "saved",
          text,
        });
      }
    }

    // Process popular terms (limit to 10)
    const now = getCurrentTimestamp();
    for (const term of popularSearchTerms.slice(0, 10)) {
      addSuggestion({
        frequency: term.count,
        id: `popular_${term.term}`,
        lastUsed: now,
        searchType: term.searchType,
        source: "popular",
        text: term.term,
      });
    }

    set({ searchSuggestions: Array.from(seen.values()) });
  },
});
