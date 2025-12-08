/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSearchResultsStore } from "@/stores/search-results-store";
import { useDestinationSearch } from "../search/use-destination-search";

interface Place {
  id: string;
  displayName?: { text: string };
  formattedAddress?: string;
  location?: { latitude: number; longitude: number };
  types?: string[];
}

const createFetchResponse = (
  places: Place[] = [],
  ok = true,
  status = 200,
  extra: Record<string, unknown> = {}
) =>
  ({
    json: vi.fn().mockResolvedValue(ok ? { places, ...extra } : extra),
    ok,
    status,
  }) as unknown as Response;

const runSearch = async (
  search: (params: {
    query: string;
    types?: string[];
    limit?: number;
  }) => Promise<void>,
  params: { query: string; types?: string[]; limit?: number }
) => {
  const promise = search(params);
  vi.runAllTimers();
  await promise;
};

describe("useDestinationSearch", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(createFetchResponse()));
    useSearchResultsStore.getState().reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    vi.clearAllMocks();
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
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      await runSearch(result.current.searchDestinations, { query: "a" });
    });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.results).toEqual([]);
    expect(result.current.searchError).toBeNull();
  });

  it("maps API response to destination results", async () => {
    const places: Place[] = [
      {
        displayName: { text: "Paris" },
        formattedAddress: "Paris, France",
        id: "paris-1",
        location: { latitude: 48.8566, longitude: 2.3522 },
        types: ["city"],
      },
      {
        displayName: { text: "Louvre" },
        formattedAddress: "Rue de Rivoli, Paris",
        id: "louvre-1",
        location: { latitude: 48.8606, longitude: 2.3376 },
        types: ["museum", "landmark"],
      },
    ];

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(createFetchResponse(places));

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
        displayName: { text: "Paris" },
        formattedAddress: "FR",
        id: "1",
        types: ["city"],
      },
      {
        displayName: { text: "France" },
        formattedAddress: "FR",
        id: "2",
        types: ["country"],
      },
      {
        displayName: { text: "Berlin" },
        formattedAddress: "DE",
        id: "3",
        types: ["city"],
      },
    ];

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(createFetchResponse(places));

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

    const body = JSON.parse(
      (fetchMock.mock.calls[0]?.[1] as RequestInit).body as string
    );
    expect(body.maxResultCount).toBe(1);
  });

  it("clamps invalid limits to API constraints", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      await runSearch(result.current.searchDestinations, { limit: -5, query: "Paris" });
    });

    const body = JSON.parse(
      (fetchMock.mock.calls[0]?.[1] as RequestInit).body as string
    );
    expect(body.maxResultCount).toBe(1);
  });

  it("surfaces API errors and clears results", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(
      createFetchResponse([], false, 500, { reason: "boom" })
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
    const pendingResolvers: Array<() => void> = [];

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementation((_, init: RequestInit) => {
      const signal = init.signal as AbortSignal;
      capturedSignals.push(signal);

      return new Promise<Response>((resolve) => {
        const complete = () => resolve(createFetchResponse([{ id: "1" } as Place]));
        pendingResolvers.push(complete);
        signal?.addEventListener("abort", () => complete(), { once: true });
      });
    });

    const { result } = renderHook(() => useDestinationSearch());

    await act(async () => {
      const firstPromise = result.current.searchDestinations({ query: "Paris" });
      vi.runAllTimers();

      const secondPromise = result.current.searchDestinations({ query: "Berlin" });
      vi.runAllTimers();

      pendingResolvers.forEach((resolve) => {
        resolve();
      });

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
