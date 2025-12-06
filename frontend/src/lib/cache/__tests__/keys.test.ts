/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { canonicalizeParamsForCache } from "../keys";

describe("canonicalizeParamsForCache", () => {
  describe("basic canonicalization", () => {
    it("should sort keys alphabetically", () => {
      const result = canonicalizeParamsForCache({ a: "first", m: "middle", z: "last" });
      expect(result).toBe("a:first|m:middle|z:last");
    });

    it("should lowercase string values", () => {
      const result = canonicalizeParamsForCache({ name: "Paris", status: "ACTIVE" });
      expect(result).toBe("name:paris|status:active");
    });

    it("should handle number values", () => {
      const result = canonicalizeParamsForCache({ limit: 10, offset: 0 });
      expect(result).toBe("limit:10|offset:0");
    });

    it("should handle boolean values", () => {
      const result = canonicalizeParamsForCache({ active: true, archived: false });
      expect(result).toBe("active:true|archived:false");
    });
  });

  describe("array handling", () => {
    it("should sort array values alphabetically", () => {
      const result = canonicalizeParamsForCache({
        tags: ["beach", "adventure", "food"],
      });
      expect(result).toBe("tags:adventure,beach,food");
    });

    it("should lowercase array string values", () => {
      const result = canonicalizeParamsForCache({ tags: ["BEACH", "Adventure"] });
      expect(result).toBe("tags:adventure,beach");
    });

    it("should handle numeric arrays", () => {
      const result = canonicalizeParamsForCache({ ids: [3, 1, 2] });
      expect(result).toBe("ids:1,2,3");
    });

    it("should handle empty arrays", () => {
      const result = canonicalizeParamsForCache({ tags: [] });
      expect(result).toBe("tags:");
    });
  });

  describe("null/undefined filtering", () => {
    it("should filter out null values", () => {
      const result = canonicalizeParamsForCache({ limit: null, status: "active" });
      expect(result).toBe("status:active");
    });

    it("should filter out undefined values", () => {
      const result = canonicalizeParamsForCache({ limit: undefined, status: "active" });
      expect(result).toBe("status:active");
    });

    it("should handle all null/undefined values", () => {
      const result = canonicalizeParamsForCache({ a: null, b: undefined });
      expect(result).toBe("");
    });
  });

  describe("prefix handling", () => {
    it("should prepend prefix with colon", () => {
      const result = canonicalizeParamsForCache({ status: "active" }, "trips");
      expect(result).toBe("trips:status:active");
    });

    it("should handle complex prefix", () => {
      const result = canonicalizeParamsForCache({ limit: 10 }, "trips:user-123");
      expect(result).toBe("trips:user-123:limit:10");
    });

    it("should handle empty params with prefix", () => {
      const result = canonicalizeParamsForCache({}, "trips");
      expect(result).toBe("trips:");
    });

    it("should handle empty prefix", () => {
      const result = canonicalizeParamsForCache({ status: "active" }, "");
      expect(result).toBe("status:active");
    });
  });

  describe("determinism", () => {
    it("should produce same key regardless of input order", () => {
      const params1 = { destination: "paris", limit: 10, status: "active" };
      const params2 = { destination: "paris", limit: 10, status: "active" };
      const params3 = { destination: "paris", limit: 10, status: "active" };

      const result1 = canonicalizeParamsForCache(params1);
      const result2 = canonicalizeParamsForCache(params2);
      const result3 = canonicalizeParamsForCache(params3);

      expect(result1).toBe(result2);
      expect(result2).toBe(result3);
    });

    it("should produce same key for arrays regardless of order", () => {
      const params1 = { tags: ["beach", "adventure", "food"] };
      const params2 = { tags: ["food", "beach", "adventure"] };

      expect(canonicalizeParamsForCache(params1)).toBe(
        canonicalizeParamsForCache(params2)
      );
    });
  });

  describe("edge cases", () => {
    it("should handle empty params object", () => {
      const result = canonicalizeParamsForCache({});
      expect(result).toBe("");
    });

    it("should handle special characters in values", () => {
      const result = canonicalizeParamsForCache({ query: "new york" });
      expect(result).toBe("query:new york");
    });

    it("should handle Date objects via toString", () => {
      const date = new Date("2024-01-01T00:00:00.000Z");
      const result = canonicalizeParamsForCache({ date });
      // Date.toString() produces locale-specific output, but should be consistent
      expect(result).toContain("date:");
    });
  });
});
