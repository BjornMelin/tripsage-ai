/** @vitest-environment jsdom */

import { renderHook, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { useActivitySearch } from "../search/use-activity-search";

describe("useActivitySearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  it("should initialize with default state", () => {
    const { result } = renderHook(() => useActivitySearch());

    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBeNull();
    expect(result.current.results).toBeNull();
    expect(result.current.searchMetadata).toBeNull();
  });

  it("should search activities successfully", async () => {
    const mockResponse = {
      activities: [
        {
          date: "2025-01-01",
          description: "Test",
          duration: 120,
          id: "places/1",
          location: "Test Location",
          name: "Test Activity",
          price: 2,
          rating: 4.5,
          type: "museum",
        },
      ],
      metadata: {
        cached: false,
        primarySource: "googleplaces" as const,
        sources: ["googleplaces" as const],
        total: 1,
      },
    };

    server.use(
      http.post("/api/activities/search", () => HttpResponse.json(mockResponse))
    );

    const { result } = renderHook(() => useActivitySearch());

    await result.current.searchActivities({ destination: "Paris" });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(false);
      expect(result.current.results).not.toBeNull();
    });

    expect(result.current.results).toHaveLength(1);
    expect(result.current.results?.[0].name).toBe("Test Activity");
    expect(result.current.searchMetadata?.total).toBe(1);
    expect(result.current.searchError).toBeNull();
  });

  it("should handle search errors", async () => {
    server.use(
      http.post("/api/activities/search", () =>
        HttpResponse.json(
          { error: "invalid_request", reason: "Invalid destination" },
          { status: 400 }
        )
      )
    );

    const { result } = renderHook(() => useActivitySearch());

    await result.current.searchActivities({ destination: "" });

    await waitFor(
      () => {
        expect(result.current.isSearching).toBe(false);
        expect(result.current.searchError).not.toBeNull();
      },
      { timeout: 3000 }
    );

    expect(result.current.searchError?.message).toContain("Invalid");
    expect(result.current.results).toBeNull();
  });

  it("should handle network errors", async () => {
    server.use(
      http.post("/api/activities/search", () =>
        HttpResponse.json({ error: "Network error" }, { status: 500 })
      )
    );

    const { result } = renderHook(() => useActivitySearch());

    await result.current.searchActivities({ destination: "Paris" });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).not.toBeNull();
    });

    expect(result.current.searchError).not.toBeNull();
    expect(result.current.results).toBeNull();
  });

  it("should reset search state", () => {
    const { result } = renderHook(() => useActivitySearch());

    // Set some state
    result.current.searchActivities({ destination: "Paris" });

    result.current.resetSearch();

    expect(result.current.results).toBeNull();
    expect(result.current.searchMetadata).toBeNull();
    expect(result.current.searchError).toBeNull();
    expect(result.current.isSearching).toBe(false);
  });

  it("should save search to local state", () => {
    const { result } = renderHook(() => useActivitySearch());

    result.current.saveSearch("My Search", { destination: "Paris" });

    expect(result.current.isSavingSearch).toBe(false);
    expect(result.current.savedSearches).toHaveLength(1);
    expect(result.current.savedSearches[0].name).toBe("My Search");
    expect(result.current.savedSearches[0].params.destination).toBe("Paris");
  });

  it("should handle save search errors", () => {
    const { result } = renderHook(() => useActivitySearch());

    // The hook's saveSearch handles errors internally
    // Since the implementation is a placeholder, we verify it doesn't crash
    result.current.saveSearch("Test", { destination: "Paris" });

    expect(result.current.isSavingSearch).toBe(false);
    expect(result.current.saveSearchError).toBeNull();
  });
});
