/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const emitOperationalAlertOncePerWindowMock = vi.hoisted(() => vi.fn());
const recordTelemetryEventMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => ({})),
}));

vi.mock("@/lib/telemetry/degraded-mode", () => ({
  emitOperationalAlertOncePerWindow: (...args: unknown[]) =>
    emitOperationalAlertOncePerWindowMock(...args),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: (...args: unknown[]) => recordTelemetryEventMock(...args),
}));

vi.mock("@/lib/telemetry/redis", () => ({
  warnRedisUnavailable: vi.fn(),
}));

const limitMock = vi.hoisted(() =>
  vi.fn(async () => ({
    limit: 0,
    pending: Promise.resolve(),
    reason: "timeout",
    remaining: 0,
    reset: 0,
    success: true,
  }))
);

vi.mock("@upstash/ratelimit", () => {
  class Ratelimit {
    static slidingWindow() {
      return () => ({});
    }

    limit() {
      return limitMock();
    }
  }

  return { Ratelimit };
});

describe("webhook rate limiting - timeout handling", () => {
  beforeEach(() => {
    vi.stubEnv("VERCEL", "1");
    vi.resetModules();
    emitOperationalAlertOncePerWindowMock.mockReset();
    recordTelemetryEventMock.mockReset();
    limitMock.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("fails closed when Upstash ratelimit times out", async () => {
    const { checkWebhookRateLimitWithPolicy } = await import("../rate-limit");
    const req = new Request("https://example.com/api/hooks/test", {
      headers: { "x-forwarded-for": "1.1.1.1" },
    });

    const res = await checkWebhookRateLimitWithPolicy(req, {
      degradedMode: "fail_closed",
    });

    expect(res).toEqual({ reason: "limiter_unavailable", success: false });
    expect(recordTelemetryEventMock).toHaveBeenCalledWith(
      "webhook.rate_limit_timeout",
      expect.objectContaining({
        level: "error",
      })
    );
    expect(emitOperationalAlertOncePerWindowMock).not.toHaveBeenCalled();
  });

  it("fails open and emits an alert when Upstash ratelimit times out", async () => {
    const { checkWebhookRateLimitWithPolicy } = await import("../rate-limit");
    const req = new Request("https://example.com/api/hooks/test", {
      headers: { "x-forwarded-for": "1.1.1.1" },
    });

    const res = await checkWebhookRateLimitWithPolicy(req, {
      degradedMode: "fail_open",
    });

    expect(res).toEqual({ reason: "limiter_unavailable", success: true });
    expect(recordTelemetryEventMock).not.toHaveBeenCalled();
    expect(emitOperationalAlertOncePerWindowMock).toHaveBeenCalledWith(
      expect.objectContaining({
        attributes: expect.objectContaining({
          degradedMode: "fail_open",
          reason: "timeout",
        }),
        event: "ratelimit.degraded",
      })
    );
  });
});
