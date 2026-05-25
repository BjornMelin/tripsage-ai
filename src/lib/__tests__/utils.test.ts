import { afterEach, describe, expect, it, vi } from "vitest";
import { clampProgress, fireAndForget } from "../utils";

const FLUSH_MICROTASKS = () => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

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

  it("handles special numeric values", () => {
    expect(clampProgress(Number.NaN)).toBe(0);
    expect(clampProgress(Number.POSITIVE_INFINITY)).toBe(100);
    expect(clampProgress(Number.NEGATIVE_INFINITY)).toBe(0);
  });
});

describe("fireAndForget", () => {
  it("passes rejected errors to the explicit error handler", async () => {
    const error = new Error("background task failed");
    const onError = vi.fn();

    fireAndForget(Promise.reject(error), onError);
    await FLUSH_MICROTASKS();

    expect(onError).toHaveBeenCalledWith(error);
  });

  it("swallows unhandled rejections without logging raw errors", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubGlobal("window", {});
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    fireAndForget(Promise.reject(new Error("sensitive background task failed")));
    await FLUSH_MICROTASKS();

    expect(warnSpy).not.toHaveBeenCalled();
  });
});
