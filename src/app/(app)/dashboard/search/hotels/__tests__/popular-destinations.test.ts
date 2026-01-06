/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import {
  DEFAULT_POPULAR_DESTINATIONS,
  mapPopularDestinationsFromApiResponse,
  POPULAR_DESTINATIONS_CACHE_TTL_MS,
  parseAvgPrice,
  readCachedPopularDestinations,
  writeCachedPopularDestinations,
} from "../popular-destinations";

class MemoryStorage implements Storage {
  private readonly data = new Map<string, string>();

  get length() {
    return this.data.size;
  }

  clear() {
    this.data.clear();
  }

  getItem(key: string) {
    return this.data.get(key) ?? null;
  }

  key(index: number) {
    return [...this.data.keys()][index] ?? null;
  }

  removeItem(key: string) {
    this.data.delete(key);
  }

  setItem(key: string, value: string) {
    this.data.set(key, value);
  }
}

describe("popular destinations helpers", () => {
  describe("parseAvgPrice", () => {
    it("parses numeric prices and ignores non-numeric values", () => {
      expect(parseAvgPrice(undefined)).toBeNull();
      expect(parseAvgPrice("free")).toBeNull();
      expect(parseAvgPrice("$199.00")).toBe(199);
      expect(parseAvgPrice("USD 1,234.56")).toBe(1234.56);
    });
  });

  describe("mapPopularDestinationsFromApiResponse", () => {
    it("returns empty list for non-array bodies", () => {
      expect(mapPopularDestinationsFromApiResponse(null)).toEqual([]);
      expect(mapPopularDestinationsFromApiResponse({})).toEqual([]);
    });

    it("maps destinations with fallback price and rating", () => {
      const parisFallback = DEFAULT_POPULAR_DESTINATIONS.find(
        (d) => d.destination === "Paris"
      );
      expect(parisFallback).not.toBeNull();

      const mapped = mapPopularDestinationsFromApiResponse([
        { city: "Paris" },
        { avgPrice: "$120", city: "Somewhere" },
        { city: "" },
      ]);

      expect(mapped).toEqual([
        {
          destination: "Paris",
          priceFrom: parisFallback?.priceFrom,
          rating: parisFallback?.rating,
        },
        { destination: "Somewhere", priceFrom: 120, rating: 4.6 },
      ]);
    });
  });

  describe("cached destinations", () => {
    it("reads and expires cached destinations based on TTL", () => {
      const storage = new MemoryStorage();
      const now = 1_000;

      writeCachedPopularDestinations(storage, now, DEFAULT_POPULAR_DESTINATIONS);

      expect(readCachedPopularDestinations(storage, now)).toEqual(
        DEFAULT_POPULAR_DESTINATIONS
      );
      expect(
        readCachedPopularDestinations(
          storage,
          now + POPULAR_DESTINATIONS_CACHE_TTL_MS - 1
        )
      ).toEqual(DEFAULT_POPULAR_DESTINATIONS);
      expect(
        readCachedPopularDestinations(
          storage,
          now + POPULAR_DESTINATIONS_CACHE_TTL_MS + 1
        )
      ).toBeNull();
    });
  });
});
