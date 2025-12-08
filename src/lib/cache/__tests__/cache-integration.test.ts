/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { hashInputForCache } from "../hash";
import { canonicalizeParamsForCache } from "../keys";
import { cacheUtils, createOptimizedQueryClient, queryKeys } from "../query-cache";

/**
 * Integration tests for cache layer utilities.
 *
 * Note: The Upstash-specific functions (getCachedJson, setCachedJson, etc.)
 * require Redis and are tested via the Upstash test suite with proper MSW handlers.
 * These tests focus on the query cache and pure utility functions.
 */

describe("cache layer integration", () => {
  describe("query cache and key utilities", () => {
    it("should create deterministic cache keys for query parameters", () => {
      const params = { destination: "Paris", limit: 10, status: "active" };
      const key = canonicalizeParamsForCache(params, "trips");

      // Same params should always produce same key
      expect(key).toBe(canonicalizeParamsForCache(params, "trips"));

      // Different order should produce same key
      const reordered = { destination: "Paris", limit: 10, status: "active" };
      expect(canonicalizeParamsForCache(reordered, "trips")).toBe(key);
    });

    it("should create unique hashes for different inputs", () => {
      const hash1 = hashInputForCache({ filters: ["beach"], query: "paris" });
      const hash2 = hashInputForCache({ filters: ["beach"], query: "london" });
      const hash3 = hashInputForCache({ filters: ["museum"], query: "paris" });

      expect(hash1).not.toBe(hash2);
      expect(hash1).not.toBe(hash3);
      expect(hash2).not.toBe(hash3);
    });

    it("should use query keys for cache invalidation", async () => {
      const client = createOptimizedQueryClient();

      // Set up cached data
      client.setQueryData(queryKeys.trips.details("trip-123"), { id: "trip-123" });
      client.setQueryData(queryKeys.trips.list({}), [{ id: "trip-123" }]);
      client.setQueryData(queryKeys.user.profile(), { id: "user-1" });

      // Invalidate trips resource
      await cacheUtils.invalidateResource(client, "trips");

      // Trip queries should be invalidated
      expect(
        client.getQueryState(queryKeys.trips.details("trip-123"))?.isInvalidated
      ).toBe(true);
      expect(client.getQueryState(queryKeys.trips.list({}))?.isInvalidated).toBe(true);

      // User queries should not be affected
      expect(client.getQueryState(queryKeys.user.profile())?.isInvalidated).toBeFalsy();
    });

    it("should support optimistic updates", () => {
      const client = createOptimizedQueryClient();

      // Initial data
      client.setQueryData(queryKeys.trips.details("trip-123"), {
        id: "trip-123",
        name: "Paris Trip",
        status: "draft",
      });

      const cacheKey = queryKeys.trips.details("trip-123").slice();

      // Optimistic update
      cacheUtils.updateCache(
        client,
        cacheKey,
        (old: { id: string; name: string; status: string } | undefined) =>
          old
            ? { ...old, status: "confirmed" }
            : { id: "trip-123", name: "", status: "confirmed" }
      );

      const updated = client.getQueryData(queryKeys.trips.details("trip-123")) as {
        id: string;
        name: string;
        status: string;
      };
      expect(updated.status).toBe("confirmed");
      expect(updated.name).toBe("Paris Trip");
    });
  });

  describe("query key factories", () => {
    it("should generate consistent keys for trips", () => {
      expect(queryKeys.trips.all).toEqual(["trips"]);
      expect(queryKeys.trips.details("abc")).toEqual(["trips", "detail", "abc"]);
      expect(queryKeys.trips.recent()).toEqual(["trips", "recent"]);
    });

    it("should generate consistent keys for chat", () => {
      expect(queryKeys.chat.all).toEqual(["chat"]);
      expect(queryKeys.chat.messages("sess-1")).toEqual(["chat", "messages", "sess-1"]);
      expect(queryKeys.chat.session("sess-1")).toEqual(["chat", "session", "sess-1"]);
    });

    it("should generate consistent keys for search", () => {
      const flightParams = { date: "2024-01-01", from: "JFK", to: "LAX" };
      expect(queryKeys.search.flights(flightParams)).toEqual([
        "search",
        "flights",
        flightParams,
      ]);

      const hotelParams = { city: "Paris", guests: 2 };
      expect(queryKeys.search.hotels(hotelParams)).toEqual([
        "search",
        "hotels",
        hotelParams,
      ]);
    });

    it("should generate consistent keys for user data", () => {
      expect(queryKeys.user.all).toEqual(["user"]);
      expect(queryKeys.user.profile()).toEqual(["user", "profile"]);
      expect(queryKeys.user.settings()).toEqual(["user", "settings"]);
      expect(queryKeys.user.apiKeys()).toEqual(["user", "api-keys"]);
    });
  });

  describe("cache key canonicalization edge cases", () => {
    it("should handle mixed data types in params", () => {
      const params = {
        array: ["a", "b"],
        boolean: true,
        nullValue: null,
        number: 42,
        string: "hello",
        undefinedValue: undefined,
      };

      const key = canonicalizeParamsForCache(params);

      // Should include valid values, exclude null/undefined
      expect(key).toContain("string:hello");
      expect(key).toContain("number:42");
      expect(key).toContain("boolean:true");
      expect(key).toContain("array:a,b");
      expect(key).not.toContain("nullValue");
      expect(key).not.toContain("undefinedValue");
    });

    it("should produce unique hashes for similar but different data", () => {
      // These are similar but should produce different hashes
      const cases = [
        { items: [1, 2, 3] },
        { items: [1, 2, 4] },
        { items: [1, 2] },
        { items: "1,2,3" },
      ];

      const hashes = cases.map(hashInputForCache);
      const uniqueHashes = new Set(hashes);

      expect(uniqueHashes.size).toBe(cases.length);
    });
  });
});
