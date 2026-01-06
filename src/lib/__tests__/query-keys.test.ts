/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { keys } from "../keys";
import { cacheTimes, staleTimes } from "../query/config";

describe("keys", () => {
  describe("memory", () => {
    it("returns base key for all()", () => {
      expect(keys.memory.all()).toEqual(["memory"]);
    });

    it("returns context key with userId", () => {
      const userId = "user-123";
      expect(keys.memory.context(userId)).toEqual(["memory", userId, "context"]);
    });

    it("returns insights key with userId", () => {
      const userId = "user-456";
      expect(keys.memory.insights(userId)).toEqual(["memory", userId, "insights"]);
    });

    it("returns search key scoped by user and params", () => {
      const params = { query: "paris" };
      expect(keys.memory.search("user-123", params)).toEqual([
        "memory",
        "user-123",
        "search",
        params,
      ]);
    });

    it("returns search key scoped by user and query string", () => {
      expect(keys.memory.search("user-123", "rome")).toEqual([
        "memory",
        "user-123",
        "search",
        "rome",
      ]);
    });

    it("uses null marker when params are omitted", () => {
      expect(keys.memory.search("user-123")).toEqual([
        "memory",
        "user-123",
        "search",
        null,
      ]);
    });

    it("returns stats key with userId", () => {
      const userId = "user-789";
      expect(keys.memory.stats(userId)).toEqual(["memory", userId, "stats"]);
    });

    it("context key extends from all()", () => {
      const baseKey = keys.memory.all();
      const contextKey = keys.memory.context("user-123");
      expect(contextKey.slice(0, baseKey.length)).toEqual(baseKey);
    });
  });

  describe("trips", () => {
    it("returns base key for all()", () => {
      expect(keys.trips.all()).toEqual(["trips"]);
    });

    it("returns lists key", () => {
      expect(keys.trips.lists("user-123")).toEqual(["trips", "user-123", "list"]);
    });

    it("returns detail key with tripId", () => {
      const tripId = 42;
      expect(keys.trips.detail("user-123", tripId)).toEqual([
        "trips",
        "user-123",
        "detail",
        tripId,
      ]);
    });

    it("returns collaborators key with tripId", () => {
      const tripId = 99;
      expect(keys.trips.collaborators("user-123", tripId)).toEqual([
        "trips",
        "user-123",
        "detail",
        tripId,
        "collaborators",
      ]);
    });

    it("returns collaboratorsDisabled key", () => {
      expect(keys.trips.collaboratorsDisabled()).toEqual([
        "trips",
        "collaborators",
        "disabled",
      ]);
    });
  });

  describe("chat", () => {
    it("returns base key for all()", () => {
      expect(keys.chat.all()).toEqual(["chat"]);
    });

    it("returns sessions key", () => {
      expect(keys.chat.sessions("user-123")).toEqual(["chat", "user-123", "sessions"]);
    });

    it("returns session key with sessionId", () => {
      const sessionId = "sess-abc";
      expect(keys.chat.session("user-123", sessionId)).toEqual([
        "chat",
        "user-123",
        "sessions",
        "session",
        sessionId,
      ]);
    });

    it("returns messages key with sessionId", () => {
      const sessionId = "sess-xyz";
      expect(keys.chat.messages("user-123", sessionId)).toEqual([
        "chat",
        "user-123",
        "sessions",
        "session",
        sessionId,
        "messages",
      ]);
    });
  });

  describe("auth", () => {
    it("returns user key", () => {
      expect(keys.auth.user()).toEqual(["auth", "user"]);
    });

    it("returns apiKeys key", () => {
      expect(keys.auth.apiKeys("user-123")).toEqual(["auth", "api-keys", "user-123"]);
    });

    it("returns permissions key with userId", () => {
      expect(keys.auth.permissions("user-123")).toEqual([
        "auth",
        "permissions",
        "user-123",
      ]);
    });
  });
});

describe("staleTimes", () => {
  it("defines stale time for trips", () => {
    expect(staleTimes.trips).toBe(2 * 60 * 1000); // 2 minutes (canonical from config.ts)
  });

  it("defines stale time for chat", () => {
    expect(staleTimes.chat).toBe(30 * 1000); // 30 seconds (canonical from config.ts)
  });

  it("defines stale time for stats", () => {
    expect(staleTimes.stats).toBe(15 * 60 * 1000); // 15 minutes
  });

  it("defines stale time for realtime", () => {
    expect(staleTimes.realtime).toBe(30 * 1000); // 30 seconds
  });

  it("defines stale time for currency", () => {
    expect(staleTimes.currency).toBe(60 * 60 * 1000); // 1 hour (canonical from config.ts)
  });

  it("all stale times are positive numbers", () => {
    for (const value of Object.values(staleTimes)) {
      expect(typeof value).toBe("number");
      expect(value).toBeGreaterThan(0);
    }
  });
});

describe("cacheTimes", () => {
  it("defines cache time levels", () => {
    expect(cacheTimes.short).toBe(5 * 60 * 1000); // 5 minutes
    expect(cacheTimes.medium).toBe(10 * 60 * 1000); // 10 minutes (canonical from config.ts)
    expect(cacheTimes.long).toBe(60 * 60 * 1000); // 1 hour (canonical from config.ts)
  });

  it("all cache times are positive numbers", () => {
    for (const value of Object.values(cacheTimes)) {
      expect(typeof value).toBe("number");
      expect(value).toBeGreaterThan(0);
    }
  });

  it("cache times are in non-decreasing order", () => {
    expect(cacheTimes.short).toBeLessThan(cacheTimes.medium);
    expect(cacheTimes.medium).toBeLessThan(cacheTimes.long);
  });
});
