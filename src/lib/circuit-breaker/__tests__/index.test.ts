/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { withFakeTimers } from "@/test/utils/with-fake-timers";

const redisMock = vi.hoisted(() => ({
  del: vi.fn(),
  eval: vi.fn(),
  get: vi.fn(),
  set: vi.fn(),
  ttl: vi.fn(),
}));

const recordTelemetryEventMock = vi.hoisted(() => vi.fn());

vi.mock("server-only", () => ({}));

vi.mock("@/lib/redis", () => ({
  getRedis: () => redisMock,
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: recordTelemetryEventMock,
  withTelemetrySpan: vi.fn(
    (
      _name: string,
      _opts: unknown,
      fn: (span: {
        recordException: ReturnType<typeof vi.fn>;
        setAttribute: ReturnType<typeof vi.fn>;
      }) => Promise<unknown>
    ) =>
      fn({
        recordException: vi.fn(),
        setAttribute: vi.fn(),
      })
  ),
}));

import { checkCircuit, getCircuitState } from "../index";

describe("circuit breaker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    redisMock.get.mockResolvedValue(null);
    redisMock.set.mockResolvedValue("OK");
  });

  it(
    "rejects open circuits with a deterministic helper-backed cooldown window",
    withFakeTimers(async () => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));
      redisMock.get.mockResolvedValueOnce(
        Date.parse("2026-02-03T04:04:46.000Z").toString()
      );

      const result = await checkCircuit({
        cooldownSeconds: 30,
        name: "maps",
      });

      expect(result).toEqual({
        allowed: false,
        reason: "Circuit open for maps, cooldown remaining: 10s",
        state: "open",
      });
    })
  );

  it(
    "stores the deterministic opened-at timestamp when the failure threshold is reached",
    withFakeTimers(async () => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));
      redisMock.get.mockResolvedValueOnce(null).mockResolvedValueOnce("5");

      const result = await checkCircuit({
        cooldownSeconds: 30,
        failureThreshold: 5,
        name: "payments",
      });

      expect(result).toEqual({
        allowed: false,
        reason: "Circuit opened for payments after 5 failures",
        state: "open",
      });
      expect(redisMock.set).toHaveBeenCalledWith(
        "circuit:payments:opened_at",
        Date.parse("2026-02-03T04:05:06.000Z").toString(),
        { ex: 60 }
      );
      expect(recordTelemetryEventMock).toHaveBeenCalledWith("circuit_breaker.opened", {
        attributes: {
          "circuit.failure_count": 5,
          "circuit.name": "payments",
          "circuit.threshold": 5,
        },
        level: "error",
      });
    })
  );

  it(
    "reports half-open state after the helper-backed cooldown has elapsed",
    withFakeTimers(async () => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));
      redisMock.get.mockResolvedValueOnce(
        Date.parse("2026-02-03T04:04:30.000Z").toString()
      );

      await expect(getCircuitState("flights", 30)).resolves.toBe("half-open");
    })
  );
});
