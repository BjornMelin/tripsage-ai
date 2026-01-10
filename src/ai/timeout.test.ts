/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { buildTimeoutConfig, buildTimeoutConfigFromSeconds } from "./timeout";

describe("buildTimeoutConfig", () => {
  it("returns undefined for invalid totals", () => {
    expect(buildTimeoutConfig()).toBeUndefined();
    expect(buildTimeoutConfig(Number.NaN)).toBeUndefined();
    expect(buildTimeoutConfig(0)).toBeUndefined();
    expect(buildTimeoutConfig(-1)).toBeUndefined();
  });

  it("normalizes short totals and clamps step duration", () => {
    const config = buildTimeoutConfig(1000);
    expect(config).toEqual({ stepMs: 5000, totalMs: 5000 });
  });

  it("uses provided step timeout when valid", () => {
    const config = buildTimeoutConfig(30_000, 10_000);
    expect(config).toEqual({ stepMs: 10_000, totalMs: 30_000 });
  });
});

describe("buildTimeoutConfigFromSeconds", () => {
  it("returns undefined for invalid seconds", () => {
    expect(buildTimeoutConfigFromSeconds()).toBeUndefined();
    expect(buildTimeoutConfigFromSeconds(Number.NaN)).toBeUndefined();
    expect(buildTimeoutConfigFromSeconds(0)).toBeUndefined();
    expect(buildTimeoutConfigFromSeconds(-5)).toBeUndefined();
  });

  it("converts seconds to milliseconds using defaults", () => {
    const config = buildTimeoutConfigFromSeconds(30);
    expect(config).toEqual({ stepMs: 20_000, totalMs: 30_000 });
  });
});
