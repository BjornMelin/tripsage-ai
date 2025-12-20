/** @vitest-environment node */

import {
  DURATION_RANGE_SCHEMA,
  type DurationRange,
  NUMERIC_RANGE_SCHEMA,
  type NumericRange,
  PRICE_RANGE_SCHEMA,
  type PriceRange,
} from "@schemas/shared/ranges";
import { describe, expect, it } from "vitest";

describe("PRICE_RANGE_SCHEMA", () => {
  describe("valid cases", () => {
    it.concurrent("should accept empty object (both optional)", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({});
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept min only", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ min: 10 });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.min).toBe(10);
        expect(result.data.max).toBeUndefined();
      }
    });

    it.concurrent("should accept max only", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ max: 100 });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.max).toBe(100);
        expect(result.data.min).toBeUndefined();
      }
    });

    it.concurrent("should accept valid range where min < max", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ max: 200, min: 50 });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.min).toBe(50);
        expect(result.data.max).toBe(200);
      }
    });

    it.concurrent("should accept valid range where min === max", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ max: 100, min: 100 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept min = 0 (nonnegative)", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ min: 0 });
      expect(result.success).toBe(true);
    });
  });

  describe("invalid cases", () => {
    it.concurrent("should reject min > max", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ max: 50, min: 200 });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toContain("min");
      }
    });

    it.concurrent("should reject negative min", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ min: -10 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject max = 0 (must be positive)", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ max: 0 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject negative max", () => {
      const result = PRICE_RANGE_SCHEMA.safeParse({ max: -5 });
      expect(result.success).toBe(false);
    });
  });

  describe("type inference", () => {
    it.concurrent("should export PriceRange type", () => {
      const range: PriceRange = { max: 100, min: 10 };
      expect(typeof range.min).toBe("number");
      expect(typeof range.max).toBe("number");
    });
  });
});

describe("DURATION_RANGE_SCHEMA", () => {
  describe("valid cases", () => {
    it.concurrent("should accept empty object (both optional)", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({});
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept min only", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ min: 30 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept max only", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ max: 120 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept valid range where min < max", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ max: 120, min: 30 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept valid range where min === max", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ max: 60, min: 60 });
      expect(result.success).toBe(true);
    });
  });

  describe("invalid cases", () => {
    it.concurrent("should reject min > max", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ max: 30, min: 180 });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toContain("min");
      }
    });

    it.concurrent("should reject min = 0 (must be positive)", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ min: 0 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject max = 0 (must be positive)", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ max: 0 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject negative values", () => {
      const result = DURATION_RANGE_SCHEMA.safeParse({ min: -10 });
      expect(result.success).toBe(false);
    });
  });

  describe("type inference", () => {
    it.concurrent("should export DurationRange type", () => {
      const range: DurationRange = { max: 120, min: 30 };
      expect(typeof range.min).toBe("number");
      expect(typeof range.max).toBe("number");
    });
  });
});

describe("NUMERIC_RANGE_SCHEMA", () => {
  describe("valid cases", () => {
    it.concurrent("should accept empty object (both optional)", () => {
      const result = NUMERIC_RANGE_SCHEMA.safeParse({});
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept negative min", () => {
      const result = NUMERIC_RANGE_SCHEMA.safeParse({ min: -100 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept zero values", () => {
      const result = NUMERIC_RANGE_SCHEMA.safeParse({ max: 0, min: 0 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept valid range", () => {
      const result = NUMERIC_RANGE_SCHEMA.safeParse({ max: 50, min: -50 });
      expect(result.success).toBe(true);
    });
  });

  describe("invalid cases", () => {
    it.concurrent("should reject min > max", () => {
      const result = NUMERIC_RANGE_SCHEMA.safeParse({ max: -100, min: 100 });
      expect(result.success).toBe(false);
    });
  });

  describe("type inference", () => {
    it.concurrent("should export NumericRange type", () => {
      const range: NumericRange = { max: 10, min: -10 };
      expect(typeof range.min).toBe("number");
    });
  });
});
