/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { cacheTimes, queryKeys, staleTimes } from "../query-keys";

describe("queryKeys", () => {
  describe("memory", () => {
    it("returns base key for all()", () => {
      expect(queryKeys.memory.all()).toEqual(["memory"]);
    });

    it("returns context key with userId", () => {
      const userId = "user-123";
      expect(queryKeys.memory.context(userId)).toEqual(["memory", "context", userId]);
    });

    it("returns insights key with userId", () => {
      const userId = "user-456";
      expect(queryKeys.memory.insights(userId)).toEqual(["memory", "insights", userId]);
    });

    it("returns search key", () => {
      expect(queryKeys.memory.search()).toEqual(["memory", "search"]);
    });

    it("returns stats key with userId", () => {
      const userId = "user-789";
      expect(queryKeys.memory.stats(userId)).toEqual(["memory", "stats", userId]);
    });

    it("context key extends from all()", () => {
      const baseKey = queryKeys.memory.all();
      const contextKey = queryKeys.memory.context("user-123");
      expect(contextKey.slice(0, baseKey.length)).toEqual(baseKey);
    });
  });

  describe("trips", () => {
    it("returns base key for all()", () => {
      expect(queryKeys.trips.all()).toEqual(["trips"]);
    });

    it("returns lists key", () => {
      expect(queryKeys.trips.lists()).toEqual(["trips", "list"]);
    });

    it("returns detail key with tripId", () => {
      const tripId = 42;
      expect(queryKeys.trips.detail(tripId)).toEqual(["trips", "detail", tripId]);
    });

    it("returns collaborators key with tripId", () => {
      const tripId = 99;
      expect(queryKeys.trips.collaborators(tripId)).toEqual([
        "trips",
        "detail",
        tripId,
        "collaborators",
      ]);
    });
  });

  describe("chat", () => {
    it("returns base key for all()", () => {
      expect(queryKeys.chat.all()).toEqual(["chat"]);
    });

    it("returns sessions key", () => {
      expect(queryKeys.chat.sessions()).toEqual(["chat", "sessions"]);
    });

    it("returns session key with sessionId", () => {
      const sessionId = "sess-abc";
      expect(queryKeys.chat.session(sessionId)).toEqual(["chat", "session", sessionId]);
    });

    it("returns messages key with sessionId", () => {
      const sessionId = "sess-xyz";
      expect(queryKeys.chat.messages(sessionId)).toEqual([
        "chat",
        "session",
        sessionId,
        "messages",
      ]);
    });
  });

  describe("auth", () => {
    it("returns user key", () => {
      expect(queryKeys.auth.user()).toEqual(["auth", "user"]);
    });

    it("returns apiKeys key", () => {
      expect(queryKeys.auth.apiKeys()).toEqual(["auth", "api-keys"]);
    });
  });
});

describe("staleTimes", () => {
  it("defines stale time for trips", () => {
    expect(staleTimes.trips).toBe(5 * 60 * 1000); // 5 minutes
  });

  it("defines stale time for chat", () => {
    expect(staleTimes.chat).toBe(1 * 60 * 1000); // 1 minute
  });

  it("defines stale time for stats", () => {
    expect(staleTimes.stats).toBe(15 * 60 * 1000); // 15 minutes
  });

  it("defines stale time for realtime", () => {
    expect(staleTimes.realtime).toBe(30 * 1000); // 30 seconds
  });

  it("all stale times are positive numbers", () => {
    for (const [_key, value] of Object.entries(staleTimes)) {
      expect(typeof value).toBe("number");
      expect(value).toBeGreaterThan(0);
    }
  });
});

describe("cacheTimes", () => {
  it("defines cache time levels", () => {
    expect(cacheTimes.short).toBe(5 * 60 * 1000); // 5 minutes
    expect(cacheTimes.medium).toBe(15 * 60 * 1000); // 15 minutes
    expect(cacheTimes.long).toBe(30 * 60 * 1000); // 30 minutes
    expect(cacheTimes.veryLong).toBe(60 * 60 * 1000); // 1 hour
  });

  it("all cache times are positive numbers", () => {
    for (const [_key, value] of Object.entries(cacheTimes)) {
      expect(typeof value).toBe("number");
      expect(value).toBeGreaterThan(0);
    }
  });

  it("cache times are in increasing order", () => {
    expect(cacheTimes.short).toBeLessThan(cacheTimes.medium);
    expect(cacheTimes.medium).toBeLessThan(cacheTimes.long);
    expect(cacheTimes.long).toBeLessThan(cacheTimes.veryLong);
  });
});
