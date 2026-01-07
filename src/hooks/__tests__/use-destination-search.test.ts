/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDestinationSearch } from "@/features/search/hooks/search/use-destination-search";
import { useSearchResultsStore } from "@/features/search/store/search-results-store";
import { server } from "@/test/msw/server";
import { createFakeTimersContext } from "@/test/utils/with-fake-timers";

interface Place {
  placeId: string;
  name: string;
  formattedAddress?: string;
  coordinates?: { lat: number; lng: number };
  types: string[];
}

const runSearch = async (
  search: (params: {
    query: string;
    types?: string[];
    limit?: number;
  }) => Promise<void>,
  params: { query: string; types?: string[]; limit?: number }
) => {
  const promise = search(params);
  await vi.runAllTimersAsync();
  await promise;
};

describe("useDestinationSearch", () => {
  const timers = createFakeTimersContext({ shouldAdvanceTime: true });

  beforeEach(() => {
    timers.setup();
    useSearchResultsStore.getState().reset();
    vi.clearAllMocks();
  });

  afterEach(() => {
    timers.teardown();
    server.resetHandlers();
    useSearchResultsStore.getState().reset();
    localStorage.clear();
  });

  it("initializes with default state", () => {
    const { result } = renderHook(() => useDestinationSearch());

    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBeNull();
    expect(result.current.results).toEqual([]);
  });

  it("returns early for short queries without calling the API", async () => {
    let apiCalled = false;
    server.use(
      http.post("/api/places/search", () => {
        apiCalled = true;
        return HttpResponse.json({ places: [] });
      })
    );

    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      await runSearch(result.current.searchDestinations, { query: "a" });
    });

    expect(apiCalled).toBe(false);
    expect(result.current.results).toEqual([]);
    expect(result.current.searchError).toBeNull();
  });

  it("maps API response to destination results", async () => {
    const places: Place[] = [
      {
        coordinates: { lat: 48.8566, lng: 2.3522 },
        formattedAddress: "Paris, France",
        name: "Paris",
        placeId: "paris-1",
        types: ["city"],
      },
      {
        coordinates: { lat: 48.8606, lng: 2.3376 },
        formattedAddress: "Rue de Rivoli, Paris",
        name: "Louvre",
        placeId: "louvre-1",
        types: ["museum", "landmark"],
      },
    ];

    server.use(http.post("/api/places/search", () => HttpResponse.json({ places })));

    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      await runSearch(result.current.searchDestinations, { limit: 5, query: "Paris" });
    });

    expect(result.current.searchError).toBeNull();
    expect(result.current.results).toHaveLength(2);
    expect(result.current.results[0]).toMatchObject({
      address: "Paris, France",
      location: { lat: 48.8566, lng: 2.3522 },
      name: "Paris",
      placeId: "paris-1",
      types: ["city"],
    });
  });

  it("filters by provided types and respects limit", async () => {
    const places: Place[] = [
      {
        formattedAddress: "FR",
        name: "Paris",
        placeId: "1",
        types: ["city"],
      },
      {
        formattedAddress: "FR",
        name: "France",
        placeId: "2",
        types: ["country"],
      },
      {
        formattedAddress: "DE",
        name: "Berlin",
        placeId: "3",
        types: ["city"],
      },
    ];

    const captured: { body: Record<string, unknown> | null } = { body: null };
    server.use(
      http.post("/api/places/search", async ({ request }) => {
        captured.body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ places });
      })
    );

    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      await runSearch(result.current.searchDestinations, {
        limit: 1,
        query: "Europe",
        types: ["city"],
      });
    });

    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].types).toContain("city");
    expect(captured.body?.maxResultCount).toBe(1);
  });

  it("clamps invalid limits to API constraints", async () => {
    const captured: { body: Record<string, unknown> | null } = { body: null };
    server.use(
      http.post("/api/places/search", async ({ request }) => {
        captured.body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ places: [] });
      })
    );

    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      await runSearch(result.current.searchDestinations, { limit: -5, query: "Paris" });
    });

    expect(captured.body?.maxResultCount).toBe(1);
  });

  it("surfaces API errors and clears results", async () => {
    server.use(
      http.post("/api/places/search", () =>
        HttpResponse.json({ reason: "boom" }, { status: 500 })
      )
    );

    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      await runSearch(result.current.searchDestinations, { query: "Paris" });
    });

    expect(result.current.results).toEqual([]);
    expect(result.current.searchError?.message).toContain("boom");
  });

  it("aborts in-flight searches when a new search starts", async () => {
    const capturedSignals: AbortSignal[] = [];
    let resolveFirst: (() => void) | null = null;
    let resolveSecond: (() => void) | null = null;
    let callCount = 0;

    server.use(
      http.post("/api/places/search", ({ request }) => {
        const signal = request.signal;
        capturedSignals.push(signal);
        callCount++;

        return new Promise<Response>((resolve) => {
          const complete = () =>
            resolve(
              HttpResponse.json({
                places: [{ name: "Place", placeId: "1", types: [] }],
              })
            );
          if (callCount === 1) {
            resolveFirst = complete;
          } else {
            resolveSecond = complete;
          }
          signal?.addEventListener("abort", complete, { once: true });
        });
      })
    );

    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      const firstPromise = result.current.searchDestinations({ query: "Paris" });
      await vi.runAllTimersAsync();

      const secondPromise = result.current.searchDestinations({ query: "Berlin" });
      await vi.runAllTimersAsync();

      // Complete requests
      resolveFirst?.();
      resolveSecond?.();

      await Promise.all([firstPromise, secondPromise]);
    });

    expect(capturedSignals[0]?.aborted).toBe(true);
  });

  it("resets state and aborts outstanding requests", () => {
    const { result } = renderHook(() => useDestinationSearch());

    act(() => {
      result.current.resetSearch();
    });

    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBeNull();
    expect(result.current.results).toEqual([]);
  });

  it("keeps stable function references across rerenders", () => {
    const { result, rerender } = renderHook(() => useDestinationSearch());

    const initialSearch = result.current.searchDestinations;
    const initialReset = result.current.resetSearch;

    rerender();

    expect(result.current.searchDestinations).toBe(initialSearch);
    expect(result.current.resetSearch).toBe(initialReset);
  });
});
