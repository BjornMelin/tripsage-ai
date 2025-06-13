import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useSearchResultsStore } from "./src/stores/search-results-store";

describe("Debug Test", () => {
  it("tests basic store functionality", () => {
    const { result } = renderHook(() => useSearchResultsStore());

    // Start search
    let searchId: string;
    act(() => {
      searchId = result.current.startSearch("flight", {});
    });

    console.log("After start:");
    console.log("  searchId:", searchId);
    console.log("  currentSearchId:", result.current.currentSearchId);
    console.log("  status:", result.current.status);
    console.log("  isSearching:", result.current.isSearching);

    // Set results
    act(() => {
      if (searchId) result.current.setSearchResults(searchId, {
        flights: [{ id: "test", price: 100 }],
      });
    });

    console.log("\nAfter setResults:");
    console.log("  currentSearchId:", result.current.currentSearchId);
    console.log("  status:", result.current.status);
    console.log("  results:", result.current.results);
    console.log("  hasResults:", result.current.hasResults);

    // Manual check
    const hasResultsManual = Object.keys(result.current.results).some((key) => {
      const typeResults =
        result.current.results[key as keyof typeof result.current.results];
      return Array.isArray(typeResults) && typeResults.length > 0;
    });
    console.log("  hasResults (manual):", hasResultsManual);

    expect(result.current.hasResults).toBe(true);
  });
});
