/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { withFakeTimers } from "@/test/utils/with-fake-timers";
import { isExpired, timeUntil } from "../helpers";

describe("shared store helpers", () => {
  it(
    "uses helper-backed current time for expiry checks",
    withFakeTimers(() => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));

      expect(isExpired(null)).toBe(true);
      expect(isExpired("2026-02-03T04:05:05.999Z")).toBe(true);
      expect(isExpired("2026-02-03T04:05:06.000Z")).toBe(true);
      expect(isExpired("2026-02-03T04:05:06.001Z")).toBe(false);
    })
  );

  it(
    "uses helper-backed current time for milliseconds until expiry",
    withFakeTimers(() => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));

      expect(timeUntil(null)).toBe(0);
      expect(timeUntil("2026-02-03T04:05:05.999Z")).toBe(0);
      expect(timeUntil("2026-02-03T04:05:06.250Z")).toBe(250);
    })
  );
});
