/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import {
  applyRateLimitHeaders,
  createRateLimitHeaders,
  normalizeRateLimitResetToMs,
} from "@/lib/ratelimit/headers";

describe("ratelimit headers", () => {
  describe("normalizeRateLimitResetToMs", () => {
    it("converts unix seconds to ms", () => {
      expect(normalizeRateLimitResetToMs(1_700_000_000)).toBe(1_700_000_000_000);
    });

    it("does not convert unix milliseconds", () => {
      expect(normalizeRateLimitResetToMs(1_700_000_000_000)).toBe(1_700_000_000_000);
    });

    it("does not convert boundary values outside the seconds range", () => {
      expect(normalizeRateLimitResetToMs(999_999_999)).toBe(999_999_999);
      expect(normalizeRateLimitResetToMs(10_000_000_000)).toBe(10_000_000_000);
    });
  });

  describe("createRateLimitHeaders", () => {
    it("returns empty object when no fields present", () => {
      expect(createRateLimitHeaders({})).toEqual({});
    });

    it("includes X-RateLimit fields when present", () => {
      expect(
        createRateLimitHeaders({
          limit: 10,
          remaining: 7,
          reset: 1_700_000_000_000,
        })
      ).toEqual({
        "X-RateLimit-Limit": "10",
        "X-RateLimit-Remaining": "7",
        "X-RateLimit-Reset": "1700000000000",
      });
    });

    it("normalizes reset seconds to ms", () => {
      expect(
        createRateLimitHeaders({
          reset: 1_700_000_000,
        })
      ).toEqual({
        "X-RateLimit-Reset": "1700000000000",
      });
    });

    it("includes Retry-After only when success is false and reset is present", () => {
      const nowMs = 1_700_000_000_000;
      const resetMs = nowMs + 60_000;
      expect(
        createRateLimitHeaders({ reset: resetMs, success: false }, { nowMs })[
          "Retry-After"
        ]
      ).toBe("60");

      expect(
        createRateLimitHeaders({ reset: resetMs, success: true }, { nowMs })
      ).toEqual({
        "X-RateLimit-Reset": String(resetMs),
      });

      expect(createRateLimitHeaders({ success: false }, { nowMs })).toEqual({});
    });

    it("clamps Retry-After at 0 when reset is in the past", () => {
      const nowMs = 1_700_000_000_000;
      const resetMs = nowMs - 1;
      expect(
        createRateLimitHeaders({ reset: resetMs, success: false }, { nowMs })[
          "Retry-After"
        ]
      ).toBe("0");
    });
  });

  describe("applyRateLimitHeaders", () => {
    it("applies computed headers onto a Headers object", () => {
      const target = new Headers();
      applyRateLimitHeaders(
        target,
        { limit: 5, remaining: 0, reset: 123, success: false },
        {
          nowMs: 0,
        }
      );

      expect(target.get("X-RateLimit-Limit")).toBe("5");
      expect(target.get("X-RateLimit-Remaining")).toBe("0");
      expect(target.get("X-RateLimit-Reset")).toBe("123");
      expect(target.get("Retry-After")).toBe("1");
    });
  });
});
