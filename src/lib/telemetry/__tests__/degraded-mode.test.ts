/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { withFakeTimers } from "@/test/utils/with-fake-timers";

const emitOperationalAlertMock = vi.hoisted(() => vi.fn());

vi.mock("server-only", () => ({}));

vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: emitOperationalAlertMock,
}));

import {
  emitOperationalAlertOncePerWindow,
  resetDegradedModeAlertStateForTests,
} from "../degraded-mode";

describe("emitOperationalAlertOncePerWindow", () => {
  beforeEach(() => {
    emitOperationalAlertMock.mockReset();
    resetDegradedModeAlertStateForTests();
  });

  it(
    "dedupes alerts using the helper-backed current time",
    withFakeTimers(() => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));

      emitOperationalAlertOncePerWindow({
        attributes: { degradedMode: "fail_open", rateLimitKey: "trips:create" },
        event: "ratelimit.degraded",
        severity: "warning",
        windowMs: 60_000,
      });
      emitOperationalAlertOncePerWindow({
        attributes: { degradedMode: "fail_open", rateLimitKey: "trips:create" },
        event: "ratelimit.degraded",
        severity: "warning",
        windowMs: 60_000,
      });

      expect(emitOperationalAlertMock).toHaveBeenCalledTimes(1);

      vi.setSystemTime(new Date("2026-02-03T04:06:07.000Z"));

      emitOperationalAlertOncePerWindow({
        attributes: { degradedMode: "fail_open", rateLimitKey: "trips:create" },
        event: "ratelimit.degraded",
        severity: "warning",
        windowMs: 60_000,
      });

      expect(emitOperationalAlertMock).toHaveBeenCalledTimes(2);
    })
  );
});
