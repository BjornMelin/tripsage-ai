/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/tracer";

describe("emitOperationalAlert", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-11-13T00:00:00.000Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("logs structured payload via console.error by default", () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    emitOperationalAlert("redis.unavailable", {
      attributes: { feature: "cache.tags", ignored: undefined },
    });

    expect(errorSpy).toHaveBeenCalledWith(
      "[operational-alert]",
      JSON.stringify({
        attributes: { feature: "cache.tags" },
        event: "redis.unavailable",
        severity: "error",
        source: TELEMETRY_SERVICE_NAME,
        timestamp: "2025-11-13T00:00:00.000Z",
      })
    );
  });

  it("uses console.warn for non-error severities", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    emitOperationalAlert("webhook.verification_failed", {
      attributes: { reason: "missing_secret_env" },
      severity: "warning",
    });

    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(errorSpy).not.toHaveBeenCalled();
    const loggedPayload = warnSpy.mock.calls[0]?.[1] as string;
    expect(JSON.parse(loggedPayload)).toMatchObject({
      event: "webhook.verification_failed",
      severity: "warning",
    });
  });
});
