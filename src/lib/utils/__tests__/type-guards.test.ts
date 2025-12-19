import { describe, expect, it } from "vitest";

import { isPlainObject } from "@/lib/utils/type-guards";

class ExampleClass {
  value = 123;
}

describe("isPlainObject", () => {
  it("returns true for plain object literals", () => {
    expect(isPlainObject({ a: 1 })).toBe(true);
  });

  it("returns true for Object.create(null)", () => {
    const obj = Object.create(null) as Record<string, unknown>;
    obj.foo = "bar";
    expect(isPlainObject(obj)).toBe(true);
  });

  it("returns false for arrays", () => {
    expect(isPlainObject([1, 2, 3])).toBe(false);
  });

  it("returns false for primitives and nullish values", () => {
    expect(isPlainObject("text")).toBe(false);
    expect(isPlainObject(123)).toBe(false);
    expect(isPlainObject(true)).toBe(false);
    expect(isPlainObject(null)).toBe(false);
    expect(isPlainObject(undefined)).toBe(false);
  });

  it("returns false for built-in objects", () => {
    expect(isPlainObject(new Date())).toBe(false);
    expect(isPlainObject(/pattern/)).toBe(false);
    expect(isPlainObject(new Map())).toBe(false);
    expect(isPlainObject(new Set())).toBe(false);
  });

  it("returns false for functions", () => {
    const arrow = () => true;
    const asyncFn = async () => true;
    expect(isPlainObject(arrow)).toBe(false);
    expect(isPlainObject(asyncFn)).toBe(false);
  });

  it("returns false for class instances", () => {
    expect(isPlainObject(new ExampleClass())).toBe(false);
  });
});
