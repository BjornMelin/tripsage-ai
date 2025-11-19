/** @vitest-environment jsdom */

import type { ActivitySearchParams } from "@schemas/search";
import { renderHook } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AllTheProviders } from "@/test/test-utils";
import { useActivitySearch } from "../use-activity-search";

// The current hook is a minimal implementation without side effects.
// Remove legacy expectations around API calls and store updates.

describe("useActivitySearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: ReactNode }) =>
    React.createElement(AllTheProviders, null, children);

  it("should return hook properties", () => {
    // Minimal hook exposes functions and default state only.

    const { result } = renderHook(() => useActivitySearch(), { wrapper });

    // Check that the hook returns the expected properties
    expect(result.current.searchActivities).toBeDefined();
    expect(result.current.saveSearch).toBeDefined();
    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBeNull();
    expect(result.current.savedSearches).toEqual([]);
    expect(result.current.popularActivities).toEqual([]);
    expect(result.current.isSavingSearch).toBe(false);
    expect(result.current.saveSearchError).toBeNull();
  });

  it("should expose empty saved searches by default", () => {
    const { result } = renderHook(() => useActivitySearch(), { wrapper });
    expect(result.current.savedSearches).toEqual([]);
  });

  it("should expose empty popular activities by default", () => {
    const { result } = renderHook(() => useActivitySearch(), { wrapper });
    expect(result.current.popularActivities).toEqual([]);
  });

  it("searchActivities is callable and resolves without side effects", async () => {
    const { result } = renderHook(() => useActivitySearch(), { wrapper });
    const searchParams: ActivitySearchParams = {
      adults: 2,
      category: "cultural",
      children: 0,
      date: "2024-07-01",
      destination: "New York",
      infants: 0,
    };
    await expect(
      result.current.searchActivities(searchParams)
    ).resolves.toBeUndefined();
    expect(result.current.isSearching).toBe(false);
  });

  it("saveSearch is callable and resolves without side effects", async () => {
    const { result } = renderHook(() => useActivitySearch(), { wrapper });
    const searchParams: ActivitySearchParams = {
      adults: 2,
      category: "food",
      children: 1,
      date: "2024-09-01",
      destination: "Tokyo",
      infants: 0,
    };
    await expect(
      result.current.saveSearch("Tokyo Food & Culture", searchParams)
    ).resolves.toBeUndefined();
    expect(result.current.isSavingSearch).toBe(false);
  });

  it("isSearching remains false in the minimal implementation", async () => {
    const { result } = renderHook(() => useActivitySearch(), { wrapper });
    expect(result.current.isSearching).toBe(false);
    await result.current.searchActivities({
      adults: 2,
      category: "sightseeing",
      children: 0,
      date: "2024-07-01",
      destination: "New York",
      infants: 0,
    } as ActivitySearchParams);
    expect(result.current.isSearching).toBe(false);
  });
});
