/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { getRouteRateLimitDegradedMode, ROUTE_RATE_LIMITS } from "../routes";

const FAIL_OPEN_ROUTE_KEYS = [
  "attachments:files",
  "config:agents:read",
  "config:agents:versions",
  "dashboard:metrics",
  "images:proxy",
  "itineraries:create",
  "itineraries:list",
  "places:details",
  "places:nearby",
  "places:photo",
  "places:search",
  "rag:index",
  "rag:search",
  "route-matrix",
  "security:csp-report",
  "security:events",
  "security:metrics",
  "security:sessions:list",
  "telemetry:post",
  "user-settings:get",
  "user-settings:update",
] as const;

describe("ROUTE_RATE_LIMITS", () => {
  describe("route definitions", () => {
    it.each([
      ["trips:list", { limit: 60, window: "1 m" }],
      ["trips:detail", { limit: 60, window: "1 m" }],
      ["trips:update", { limit: 30, window: "1 m" }],
      ["trips:delete", { limit: 10, window: "1 m" }],
      ["chat:sessions:create", { limit: 30, window: "1 m" }],
      ["chat:sessions:list", { limit: 60, window: "1 m" }],
      ["chat:sessions:messages:create", { limit: 40, window: "1 m" }],
      ["memory:search", { limit: 60, window: "1 m" }],
      ["memory:context", { limit: 60, window: "1 m" }],
      ["memory:stats", { limit: 30, window: "1 m" }],
      ["security:metrics", { limit: 20, window: "1 m" }],
      ["security:sessions:list", { limit: 20, window: "1 m" }],
    ])("defines rate limit for %s", (routeName, expected) => {
      expect(
        ROUTE_RATE_LIMITS[routeName as keyof typeof ROUTE_RATE_LIMITS]
      ).toMatchObject(expected);
    });
  });

  describe("type safety", () => {
    it("all keys are properly typed as RouteRateLimitKey", () => {
      expect(Object.values(ROUTE_RATE_LIMITS).length).toBeGreaterThan(0);

      for (const config of Object.values(ROUTE_RATE_LIMITS)) {
        expect(config).toHaveProperty("limit");
        expect(config).toHaveProperty("window");
        expect(typeof config.limit).toBe("number");
        expect(typeof config.window).toBe("string");
      }
    });

    it("all limits are positive integers", () => {
      for (const config of Object.values(ROUTE_RATE_LIMITS)) {
        expect(config.limit).toBeGreaterThan(0);
        expect(Number.isInteger(config.limit)).toBe(true);
      }
    });

    it("all windows use valid time format", () => {
      const validWindowPattern = /^\d+\s*(s|m|h|d)$/;
      for (const config of Object.values(ROUTE_RATE_LIMITS)) {
        expect(config.window).toMatch(validWindowPattern);
      }
    });
  });

  describe("degraded-mode policy", () => {
    it.each([
      "auth:login",
      "chat:stream",
      "config:agents:rollback",
      "config:agents:update",
      "flights:search",
      "memory:sync",
      "security:sessions:terminate",
      "trips:create",
    ] as const)("fails closed for protected key %s", (routeName) => {
      expect(getRouteRateLimitDegradedMode(routeName)).toBe("fail_closed");
    });

    it.each([
      ...FAIL_OPEN_ROUTE_KEYS,
      "geocode",
      "routes",
      "timezone",
    ] as const)("fails open for low-cost key %s", (routeName) => {
      expect(getRouteRateLimitDegradedMode(routeName)).toBe("fail_open");
    });

    it("keeps registry omissions limited to the explicit fail-open allowlist", () => {
      const omittedKeys = Object.entries(ROUTE_RATE_LIMITS)
        .filter(([, config]) => !("degradedMode" in config))
        .map(([key]) => key)
        .sort();

      expect(omittedKeys).toEqual(
        [...FAIL_OPEN_ROUTE_KEYS, "geocode", "routes", "timezone"].sort()
      );
    });
  });
});
