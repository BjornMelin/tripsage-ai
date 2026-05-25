/** @vitest-environment jsdom */

import type { MockInstance } from "vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GetAmenityIcon } from "../amenities";

describe("GetAmenityIcon", () => {
  let warnSpy: MockInstance<typeof console.warn> | undefined;

  afterEach(() => {
    warnSpy?.mockRestore();
    warnSpy = undefined;
  });

  it("returns an icon component for supported amenities", () => {
    const Icon = GetAmenityIcon("wifi");

    expect(Icon).toBeDefined();
  });

  it("returns undefined for unknown amenities without logging raw diagnostics", () => {
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    expect(GetAmenityIcon("free_wifi")).toBeUndefined();
    expect(warnSpy).not.toHaveBeenCalled();
  });
});
