/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { GetAmenityIcon } from "../amenities";

describe("GetAmenityIcon", () => {
  it("returns an icon component for supported amenities", () => {
    const Icon = GetAmenityIcon("wifi");

    expect(Icon).toBeDefined();
  });

  it("returns undefined for unknown amenities without logging raw diagnostics", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    expect(GetAmenityIcon("free_wifi")).toBeUndefined();
    expect(warnSpy).not.toHaveBeenCalled();

    warnSpy.mockRestore();
  });
});
