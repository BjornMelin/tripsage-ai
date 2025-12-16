import { describe, expect, it } from "vitest";
import { clampProgress } from "../utils";

describe("clampProgress", () => {
  it("returns value within range unchanged", () => {
    expect(clampProgress(50)).toBe(50);
    expect(clampProgress(0)).toBe(0);
    expect(clampProgress(100)).toBe(100);
  });

  it("clamps values below 0 to 0", () => {
    expect(clampProgress(-10)).toBe(0);
    expect(clampProgress(-1)).toBe(0);
    expect(clampProgress(-100)).toBe(0);
  });

  it("clamps values above 100 to 100", () => {
    expect(clampProgress(150)).toBe(100);
    expect(clampProgress(101)).toBe(100);
    expect(clampProgress(999)).toBe(100);
  });

  it("handles decimal values", () => {
    expect(clampProgress(50.5)).toBe(50.5);
    expect(clampProgress(-0.1)).toBe(0);
    expect(clampProgress(100.1)).toBe(100);
  });
});
