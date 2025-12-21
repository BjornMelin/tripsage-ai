import { describe, expect, it } from "vitest";

import { deepEqualJsonLike } from "@/lib/utils/deep-equal";

describe("deepEqualJsonLike", () => {
  it("compares primitives and arrays", () => {
    expect(deepEqualJsonLike(1, 1)).toBe(true);
    expect(deepEqualJsonLike(1, 2)).toBe(false);
    expect(deepEqualJsonLike(["a", "b"], ["a", "b"])).toBe(true);
    expect(deepEqualJsonLike(["a", "b"], ["a", "c"])).toBe(false);
  });

  it("treats undefined object properties as absent", () => {
    expect(deepEqualJsonLike({ a: 1, b: undefined }, { a: 1 })).toBe(true);
    expect(deepEqualJsonLike({ a: 1 }, { a: 1, b: undefined })).toBe(true);
    expect(deepEqualJsonLike({ a: { b: undefined } }, { a: {} })).toBe(true);
  });

  it("returns false when priority keys differ", () => {
    expect(
      deepEqualJsonLike(
        { extra: { deep: ["x", "y"] }, origin: "NYC" },
        { extra: { deep: ["x", "y"] }, origin: "LAX" }
      )
    ).toBe(false);
  });

  it("guards against excessive depth (including cyclic inputs) and logs once at root", () => {
    const warnings: Array<{ message: string; meta?: Record<string, unknown> }> = [];
    const logger = {
      warn: (message: string, meta?: Record<string, unknown>) => {
        warnings.push({ message, meta });
      },
    };

    const a: Record<string, unknown> = {};
    a.self = a;
    const b: Record<string, unknown> = {};
    b.self = b;

    const result = deepEqualJsonLike(a, b, { logger, maxDepth: 3 });
    expect(result).toBe(false);
    expect(
      warnings.some((w) => w.message === "deepEqualJsonLike maxDepth exceeded")
    ).toBe(true);
  });

  it("logs slow comparisons when duration exceeds threshold", () => {
    const warnings: Array<{ message: string; meta?: Record<string, unknown> }> = [];
    const logger = {
      warn: (message: string, meta?: Record<string, unknown>) => {
        warnings.push({ message, meta });
      },
    };

    let call = 0;
    const nowMs = () => {
      call += 1;
      return call === 1 ? 0 : 10;
    };

    const result = deepEqualJsonLike(
      { a: 1 },
      { a: 1 },
      { logger, nowMs, slowThresholdMs: 0 }
    );
    expect(result).toBe(true);
    expect(warnings.some((w) => w.message === "Slow dirty-check comparison")).toBe(
      true
    );
  });

  it("handles large arrays", () => {
    const a = Array.from({ length: 1_000 }, (_, i) => i);
    const b = Array.from({ length: 1_000 }, (_, i) => i);
    expect(deepEqualJsonLike(a, b)).toBe(true);
    b[999] = 1_001;
    expect(deepEqualJsonLike(a, b)).toBe(false);
  });
});
