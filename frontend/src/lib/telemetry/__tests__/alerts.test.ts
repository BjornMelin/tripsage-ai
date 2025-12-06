/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/constants";

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
}));

import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

const mockRecordTelemetryEvent = vi.mocked(recordTelemetryEvent);

describe("emitOperationalAlert", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-11-13T00:00:00.000Z"));
    mockRecordTelemetryEvent.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("records error severity alert via OTel with default error level", () => {
    emitOperationalAlert("redis.unavailable", {
      attributes: { feature: "cache.tags", ignored: undefined },
    });

    expect(mockRecordTelemetryEvent).toHaveBeenCalledWith(
      "alert.redis.unavailable",
      expect.objectContaining({
        attributes: {
          "alert.severity": "error",
          "alert.source": TELEMETRY_SERVICE_NAME,
          "alert.timestamp": "2025-11-13T00:00:00.000Z",
          feature: "cache.tags",
        },
        level: "error",
      })
    );
  });

  it("records warning severity alert via OTel", () => {
    emitOperationalAlert("webhook.verification_failed", {
      attributes: { reason: "missing_secret_env" },
      severity: "warning",
    });

    expect(mockRecordTelemetryEvent).toHaveBeenCalledWith(
      "alert.webhook.verification_failed",
      expect.objectContaining({
        attributes: expect.objectContaining({
          "alert.severity": "warning",
          reason: "missing_secret_env",
        }),
        level: "warning",
      })
    );
  });

  it("records info severity alert via OTel", () => {
    emitOperationalAlert("deployment.completed", {
      attributes: { version: "1.2.3" },
      severity: "info",
    });

    expect(mockRecordTelemetryEvent).toHaveBeenCalledWith(
      "alert.deployment.completed",
      expect.objectContaining({
        attributes: expect.objectContaining({
          "alert.severity": "info",
          version: "1.2.3",
        }),
        level: "info",
      })
    );
  });

  it("filters out undefined attributes", () => {
    const attributesMatcher = {
      asymmetricMatch: (value: Record<string, unknown>) =>
        value !== null &&
        typeof value === "object" &&
        value.defined === "value" &&
        value.empty === "" &&
        value.zero === 0 &&
        !Object.hasOwn(value, "undefined"),
      toString: () => "attributes without undefined key",
    };

    emitOperationalAlert("test.event", {
      attributes: {
        defined: "value",
        empty: "",
        undefined: undefined,
        zero: 0,
      },
    });

    expect(mockRecordTelemetryEvent).toHaveBeenCalledWith(
      "alert.test.event",
      expect.objectContaining({
        attributes: attributesMatcher,
      })
    );
  });
});
