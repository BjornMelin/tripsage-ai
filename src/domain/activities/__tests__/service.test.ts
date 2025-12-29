/** @vitest-environment node */

import type { Activity, ActivitySearchParams } from "@schemas/search";
import { describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { NotFoundError } from "../errors";
import type { ActivitiesCache, PlacesActivitiesAdapter, WebSearchFn } from "../service";
import { ActivitiesService } from "../service";

function makeActivity(partial: Partial<Activity> & Pick<Activity, "id">): Activity {
  return {
    coordinates: partial.coordinates,
    date: partial.date ?? "2025-01-01",
    description: partial.description ?? "desc",
    duration: partial.duration ?? 120,
    id: partial.id,
    images: partial.images,
    location: partial.location ?? "somewhere",
    name: partial.name ?? "name",
    price: partial.price ?? 2,
    rating: partial.rating ?? 4.2,
    type: partial.type ?? "activity",
  };
}

function makePlacesAdapter(
  overrides?: Partial<PlacesActivitiesAdapter>
): PlacesActivitiesAdapter {
  return {
    buildSearchQuery: vi.fn((destination: string, category?: string) =>
      [destination, category].filter(Boolean).join(" ")
    ),
    getDetails: vi.fn(async (_placeId: string) => null),
    search: vi.fn(async (_query: string, _limit: number) => []),
    ...overrides,
  };
}

function makeCache(overrides?: Partial<ActivitiesCache>): ActivitiesCache {
  return {
    findActivityInRecentSearches: vi.fn(async () => null),
    getSearch: vi.fn(async () => null),
    putSearch: vi.fn(async () => undefined),
    ...overrides,
  };
}

describe("ActivitiesService", () => {
  it("throws when destination is missing", async () => {
    const service = new ActivitiesService({
      hashInput: () => "hash",
      places: makePlacesAdapter(),
    });

    await expect(
      service.search(unsafeCast<ActivitySearchParams>({}), {})
    ).rejects.toThrow("Destination is required");
  });

  it("returns cached results when available (skips Places)", async () => {
    const cachedActivity = makeActivity({ id: "places/1", name: "Cached Activity" });
    const cache = makeCache({
      getSearch: vi.fn(async (_input) => ({
        results: [cachedActivity],
        source: "cached" as const,
      })),
    });
    const places = makePlacesAdapter();
    const service = new ActivitiesService({
      cache,
      hashInput: () => "hash",
      places,
    });

    const result = await service.search({ destination: "Paris" }, { userId: "user-1" });

    expect(result.metadata.cached).toBe(true);
    expect(result.metadata.primarySource).toBe("googleplaces");
    expect(result.metadata.sources).toEqual(["cached"]);
    expect(result.activities).toEqual([cachedActivity]);
    expect(places.search).not.toHaveBeenCalled();
  });

  it("performs Places search on cache miss and writes to cache", async () => {
    const placesActivity = makeActivity({ id: "places/1", name: "Museum" });
    const cache = makeCache();
    const places = makePlacesAdapter({
      search: vi.fn(async () => [placesActivity]),
    });
    const service = new ActivitiesService({
      cache,
      hashInput: () => "qhash",
      places,
    });

    const result = await service.search(
      { category: "museums", destination: "New York" },
      { userId: "user-1" }
    );

    expect(result.metadata.cached).toBe(false);
    expect(result.metadata.primarySource).toBe("googleplaces");
    expect(result.metadata.sources).toEqual(["googleplaces"]);
    expect(result.activities).toEqual([placesActivity]);
    expect(cache.putSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        destination: "New York",
        queryHash: "qhash",
        source: "googleplaces",
        userId: "user-1",
      })
    );
  });

  it("triggers fallback when Places returns zero results", async () => {
    const cache = makeCache();
    const places = makePlacesAdapter({
      search: vi.fn(async () => []),
    });
    const webSearch: WebSearchFn = vi.fn(async () => ({
      results: [{ title: "Hidden Gem", url: "https://example.com/activity" }],
    }));
    const service = new ActivitiesService({
      cache,
      hashInput: () => "qhash",
      places,
      webSearch,
    });

    const result = await service.search(
      { destination: "Unknown City" },
      { userId: "user-1" }
    );

    expect(webSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        query: "things to do in Unknown City",
        toolCallId: "activities:webSearch:qhash",
      })
    );
    expect(result.metadata.primarySource).toBe("ai_fallback");
    expect(result.metadata.sources).toEqual(["googleplaces", "ai_fallback"]);
    expect(result.metadata.notes).toEqual(
      expect.arrayContaining([expect.stringContaining("AI suggestions")])
    );
    expect(result.activities.some((a) => a.id.startsWith("ai_fallback:"))).toBe(true);
  });

  it("does not trigger fallback when Places returns sufficient results", async () => {
    const places = makePlacesAdapter({
      search: vi.fn(async () => [
        makeActivity({ id: "places/1" }),
        makeActivity({ id: "places/2" }),
        makeActivity({ id: "places/3" }),
        makeActivity({ id: "places/4" }),
        makeActivity({ id: "places/5" }),
      ]),
    });
    const webSearch: WebSearchFn = vi.fn(async () => ({
      results: [{ title: "Should Not Be Used", url: "https://example.com/nope" }],
    }));
    const service = new ActivitiesService({
      hashInput: () => "qhash",
      places,
      webSearch,
    });

    const result = await service.search(
      { destination: "SmallTown" },
      { userId: "user-1" }
    );

    expect(webSearch).not.toHaveBeenCalled();
    expect(result.metadata.primarySource).toBe("googleplaces");
    expect(result.metadata.sources).toEqual(["googleplaces"]);
  });

  it("triggers mixed fallback when destination is popular and results are few", async () => {
    const places = makePlacesAdapter({
      search: vi.fn(async () => [
        makeActivity({ id: "places/1" }),
        makeActivity({ id: "places/2" }),
      ]),
    });
    const webSearch: WebSearchFn = vi.fn(async () => ({
      results: [{ title: "Extra Idea", url: "https://example.com/extra" }],
    }));
    const cache = makeCache();
    const service = new ActivitiesService({
      cache,
      hashInput: () => "qhash",
      places,
      webSearch,
    });

    const result = await service.search({ destination: "Paris" }, { userId: "user-1" });

    expect(webSearch).toHaveBeenCalled();
    expect(result.metadata.primarySource).toBe("mixed");
    expect(result.metadata.sources).toEqual(["googleplaces", "ai_fallback"]);
    expect(cache.putSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        source: "googleplaces",
      })
    );
  });

  it("details returns cached activity when available", async () => {
    const cached = makeActivity({ id: "places/123", name: "Cached" });
    const cache = makeCache({
      findActivityInRecentSearches: vi.fn(async () => cached),
    });
    const places = makePlacesAdapter({
      getDetails: vi.fn(async () =>
        makeActivity({ id: "places/123", name: "From Places" })
      ),
    });
    const service = new ActivitiesService({
      cache,
      hashInput: () => "hash",
      places,
    });

    const result = await service.details("places/123", { userId: "user-1" });

    expect(result).toEqual(cached);
    expect(places.getDetails).not.toHaveBeenCalled();
  });

  it("details throws NotFoundError when Places returns null", async () => {
    const places = makePlacesAdapter({
      getDetails: vi.fn(async () => null),
    });
    const service = new ActivitiesService({
      hashInput: () => "hash",
      places,
    });

    await expect(
      service.details("missing", { userId: "user-1" })
    ).rejects.toBeInstanceOf(NotFoundError);
  });
});
