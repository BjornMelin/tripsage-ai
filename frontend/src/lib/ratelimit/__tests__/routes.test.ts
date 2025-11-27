/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { ROUTE_RATE_LIMITS, type RouteRateLimitKey } from "../routes";

describe("ROUTE_RATE_LIMITS", () => {
  describe("trips routes", () => {
    it("defines rate limit for trips:list", () => {
      expect(ROUTE_RATE_LIMITS["trips:list"]).toEqual({
        limit: 60,
        window: "1 m",
      });
    });

    it("defines rate limit for trips:detail", () => {
      expect(ROUTE_RATE_LIMITS["trips:detail"]).toEqual({
        limit: 60,
        window: "1 m",
      });
    });

    it("defines rate limit for trips:update", () => {
      expect(ROUTE_RATE_LIMITS["trips:update"]).toEqual({
        limit: 30,
        window: "1 m",
      });
    });

    it("defines rate limit for trips:delete", () => {
      expect(ROUTE_RATE_LIMITS["trips:delete"]).toEqual({
        limit: 10,
        window: "1 m",
      });
    });
  });

  describe("chat session routes", () => {
    it("defines rate limit for chat:sessions:create", () => {
      expect(ROUTE_RATE_LIMITS["chat:sessions:create"]).toEqual({
        limit: 30,
        window: "1 m",
      });
    });

    it("defines rate limit for chat:sessions:list", () => {
      expect(ROUTE_RATE_LIMITS["chat:sessions:list"]).toEqual({
        limit: 60,
        window: "1 m",
      });
    });

    it("defines rate limit for chat:sessions:messages:create", () => {
      expect(ROUTE_RATE_LIMITS["chat:sessions:messages:create"]).toEqual({
        limit: 40,
        window: "1 m",
      });
    });
  });

  describe("memory routes", () => {
    it("defines rate limit for memory:search", () => {
      expect(ROUTE_RATE_LIMITS["memory:search"]).toEqual({
        limit: 60,
        window: "1 m",
      });
    });

    it("defines rate limit for memory:context", () => {
      expect(ROUTE_RATE_LIMITS["memory:context"]).toEqual({
        limit: 60,
        window: "1 m",
      });
    });

    it("defines rate limit for memory:stats", () => {
      expect(ROUTE_RATE_LIMITS["memory:stats"]).toEqual({
        limit: 30,
        window: "1 m",
      });
    });
  });

  describe("security routes", () => {
    it("defines rate limit for security:metrics", () => {
      expect(ROUTE_RATE_LIMITS["security:metrics"]).toEqual({
        limit: 20,
        window: "1 m",
      });
    });

    it("defines rate limit for security:sessions:list", () => {
      expect(ROUTE_RATE_LIMITS["security:sessions:list"]).toEqual({
        limit: 20,
        window: "1 m",
      });
    });
  });

  describe("type safety", () => {
    it("all keys are properly typed as RouteRateLimitKey", () => {
      const keys = Object.keys(ROUTE_RATE_LIMITS) as RouteRateLimitKey[];
      expect(keys.length).toBeGreaterThan(0);

      // Verify each key has the expected shape
      for (const key of keys) {
        const config = ROUTE_RATE_LIMITS[key];
        expect(config).toHaveProperty("limit");
        expect(config).toHaveProperty("window");
        expect(typeof config.limit).toBe("number");
        expect(typeof config.window).toBe("string");
      }
    });

    it("all limits are positive integers", () => {
      for (const [_key, config] of Object.entries(ROUTE_RATE_LIMITS)) {
        expect(config.limit).toBeGreaterThan(0);
        expect(Number.isInteger(config.limit)).toBe(true);
      }
    });

    it("all windows use valid time format", () => {
      const validWindowPattern = /^\d+\s*(s|m|h|d)$/;
      for (const [_key, config] of Object.entries(ROUTE_RATE_LIMITS)) {
        expect(config.window).toMatch(validWindowPattern);
      }
    });
  });
});
