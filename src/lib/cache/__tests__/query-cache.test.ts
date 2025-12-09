/** @vitest-environment jsdom */

import { QueryClient } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cacheUtils, createOptimizedQueryClient, queryKeys } from "../query-cache";

describe("createOptimizedQueryClient", () => {
  it("should create a QueryClient instance", () => {
    const client = createOptimizedQueryClient();
    expect(client).toBeInstanceOf(QueryClient);
  });

  it("should have correct default staleTime", () => {
    const client = createOptimizedQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.staleTime).toBe(5 * 60 * 1000); // 5 minutes
  });

  it("should have correct default gcTime", () => {
    const client = createOptimizedQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.gcTime).toBe(10 * 60 * 1000); // 10 minutes
  });

  it("should have refetchOnWindowFocus disabled", () => {
    const client = createOptimizedQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });

  it("should have retry disabled for 4xx errors", () => {
    const client = createOptimizedQueryClient();
    const defaults = client.getDefaultOptions();
    const retryFn = defaults.queries?.retry as (
      failureCount: number,
      error: unknown
    ) => boolean;

    // 4xx errors should not retry
    expect(retryFn(0, { status: 400 })).toBe(false);
    expect(retryFn(0, { status: 404 })).toBe(false);
    expect(retryFn(0, { status: 499 })).toBe(false);
  });

  it("should retry server errors up to 3 times", () => {
    const client = createOptimizedQueryClient();
    const defaults = client.getDefaultOptions();
    const retryFn = defaults.queries?.retry as (
      failureCount: number,
      error: unknown
    ) => boolean;

    // 5xx errors should retry up to 3 times
    expect(retryFn(0, { status: 500 })).toBe(true);
    expect(retryFn(1, { status: 500 })).toBe(true);
    expect(retryFn(2, { status: 500 })).toBe(true);
    expect(retryFn(3, { status: 500 })).toBe(false);
  });

  it("should have exponential backoff for retry delay", () => {
    const client = createOptimizedQueryClient();
    const defaults = client.getDefaultOptions();
    const retryDelayFn = defaults.queries?.retryDelay as (
      attemptIndex: number
    ) => number;

    expect(retryDelayFn(0)).toBe(1000); // 1s
    expect(retryDelayFn(1)).toBe(2000); // 2s
    expect(retryDelayFn(2)).toBe(4000); // 4s
    expect(retryDelayFn(3)).toBe(8000); // 8s
    expect(retryDelayFn(5)).toBe(30000); // max 30s
    expect(retryDelayFn(10)).toBe(30000); // capped at 30s
  });
});

describe("cacheUtils", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createOptimizedQueryClient();
  });

  describe("clearAll", () => {
    it("should clear all cached queries", () => {
      // Set up some cached data
      queryClient.setQueryData(["test", "1"], { data: "one" });
      queryClient.setQueryData(["test", "2"], { data: "two" });

      expect(queryClient.getQueryData(["test", "1"])).toBeDefined();

      cacheUtils.clearAll(queryClient);

      expect(queryClient.getQueryData(["test", "1"])).toBeUndefined();
      expect(queryClient.getQueryData(["test", "2"])).toBeUndefined();
    });
  });

  describe("invalidateResource", () => {
    it("should invalidate queries for specific resource", async () => {
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      await cacheUtils.invalidateResource(queryClient, "trips");

      expect(invalidateSpy).toHaveBeenCalledWith({
        predicate: expect.any(Function),
      });
    });

    it("should match queries with resource as first element", async () => {
      queryClient.setQueryData(["trips", "123"], { id: "123" });
      queryClient.setQueryData(["trips", "list"], []);
      queryClient.setQueryData(["users", "456"], { id: "456" });

      await cacheUtils.invalidateResource(queryClient, "trips");

      // After invalidation, queries should be marked as stale
      const tripsState = queryClient.getQueryState(["trips", "123"]);
      const usersState = queryClient.getQueryState(["users", "456"]);

      expect(tripsState?.isInvalidated).toBe(true);
      expect(usersState?.isInvalidated).toBeFalsy();
    });
  });

  describe("updateCache", () => {
    it("should optimistically update cache", () => {
      queryClient.setQueryData(["count"], 0);

      cacheUtils.updateCache(
        queryClient,
        ["count"],
        (old: number | undefined) => (old ?? 0) + 1
      );

      expect(queryClient.getQueryData(["count"])).toBe(1);
    });

    it("should handle undefined old data", () => {
      cacheUtils.updateCache(
        queryClient,
        ["new-key"],
        (old: unknown) => old ?? { default: true }
      );

      expect(queryClient.getQueryData(["new-key"])).toEqual({ default: true });
    });
  });

  describe("prefetchCritical", () => {
    it("should attempt to prefetch critical queries", async () => {
      const prefetchSpy = vi
        .spyOn(queryClient, "prefetchQuery")
        .mockResolvedValue(undefined);

      await cacheUtils.prefetchCritical(queryClient);

      // Should attempt to prefetch user profile and recent trips
      expect(prefetchSpy).toHaveBeenCalledTimes(2);

      // Verify the query keys being prefetched
      const calls = prefetchSpy.mock.calls;
      const queryKeys = calls.map((call) => call[0].queryKey);
      expect(queryKeys).toContainEqual(["user", "profile"]);
      expect(queryKeys).toContainEqual(["trips", "recent"]);
    });
  });
});

describe("queryKeys", () => {
  describe("trips", () => {
    it("should return correct all trips key", () => {
      expect(queryKeys.trips.all).toEqual(["trips"]);
    });

    it("should return correct trip details key", () => {
      expect(queryKeys.trips.details("trip-123")).toEqual([
        "trips",
        "detail",
        "trip-123",
      ]);
    });

    it("should return correct trips list key with filters", () => {
      const filters = { limit: 10, status: "active" };
      expect(queryKeys.trips.list(filters)).toEqual(["trips", "list", filters]);
    });

    it("should return correct recent trips key", () => {
      expect(queryKeys.trips.recent()).toEqual(["trips", "recent"]);
    });
  });

  describe("chat", () => {
    it("should return correct all chat key", () => {
      expect(queryKeys.chat.all).toEqual(["chat"]);
    });

    it("should return correct messages key", () => {
      expect(queryKeys.chat.messages("session-abc")).toEqual([
        "chat",
        "messages",
        "session-abc",
      ]);
    });

    it("should return correct session key", () => {
      expect(queryKeys.chat.session("sess-123")).toEqual([
        "chat",
        "session",
        "sess-123",
      ]);
    });

    it("should return correct sessions list key", () => {
      expect(queryKeys.chat.sessions()).toEqual(["chat", "sessions"]);
    });
  });

  describe("user", () => {
    it("should return correct all user key", () => {
      expect(queryKeys.user.all).toEqual(["user"]);
    });

    it("should return correct profile key", () => {
      expect(queryKeys.user.profile()).toEqual(["user", "profile"]);
    });

    it("should return correct settings key", () => {
      expect(queryKeys.user.settings()).toEqual(["user", "settings"]);
    });

    it("should return correct api keys key", () => {
      expect(queryKeys.user.apiKeys()).toEqual(["user", "api-keys"]);
    });
  });

  describe("search", () => {
    it("should return correct destinations search key", () => {
      expect(queryKeys.search.destinations("paris")).toEqual([
        "search",
        "destinations",
        "paris",
      ]);
    });

    it("should return correct flights search key", () => {
      const params = { from: "NYC", to: "LAX" };
      expect(queryKeys.search.flights(params)).toEqual(["search", "flights", params]);
    });

    it("should return correct hotels search key", () => {
      const params = { checkIn: "2024-01-01", city: "Paris" };
      expect(queryKeys.search.hotels(params)).toEqual(["search", "hotels", params]);
    });

    it("should return correct activities search key", () => {
      const params = { category: "tours", location: "Rome" };
      expect(queryKeys.search.activities(params)).toEqual([
        "search",
        "activities",
        params,
      ]);
    });
  });

  describe("agents", () => {
    it("should return correct all agents key", () => {
      expect(queryKeys.agents.all).toEqual(["agents"]);
    });

    it("should return correct agent metrics key", () => {
      expect(queryKeys.agents.metrics("agent-1")).toEqual([
        "agents",
        "metrics",
        "agent-1",
      ]);
    });

    it("should return correct agent status key", () => {
      expect(queryKeys.agents.status()).toEqual(["agents", "status"]);
    });
  });
});
