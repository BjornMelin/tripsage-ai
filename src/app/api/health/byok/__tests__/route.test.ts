/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest } from "@/test/helpers/route";

vi.mock("server-only", () => ({}));

const ENV_STATE = vi.hoisted(() => ({
  byokHealthcheckKey: "test-byok-health-key-123456789012345",
}));
const TEST_HEALTH_KEY = ENV_STATE.byokHealthcheckKey;
const MOCK_CHECK_BYOK_VAULT_HEALTH = vi.hoisted(() => vi.fn());
const MOCK_SPAN = vi.hoisted(() => ({
  setAttribute: vi.fn(),
}));
const MOCK_RECORD_ERROR_ON_SPAN = vi.hoisted(() => vi.fn());
const MOCK_RECORD_TELEMETRY_EVENT = vi.hoisted(() => vi.fn());
const MOCK_WITH_TELEMETRY_SPAN = vi.hoisted(() =>
  vi.fn(
    (_name: string, _options: unknown, execute: (span: typeof MOCK_SPAN) => unknown) =>
      execute(MOCK_SPAN)
  )
);

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn((key: string, fallback: unknown) =>
    key === "BYOK_HEALTHCHECK_KEY" ? ENV_STATE.byokHealthcheckKey : fallback
  ),
}));

vi.mock("@/lib/supabase/rpc", () => ({
  checkByokVaultHealth: MOCK_CHECK_BYOK_VAULT_HEALTH,
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordErrorOnSpan: MOCK_RECORD_ERROR_ON_SPAN,
  recordTelemetryEvent: MOCK_RECORD_TELEMETRY_EVENT,
  withTelemetrySpan: MOCK_WITH_TELEMETRY_SPAN,
}));

function byokHealthRequest(headers?: Record<string, string>): NextRequest {
  return createMockNextRequest({
    headers,
    method: "GET",
    url: "http://localhost/api/health/byok",
  });
}

function mockPerformanceNowSequence(values: number[]) {
  const nowSpy = vi.spyOn(performance, "now");
  for (const value of values) {
    nowSpy.mockReturnValueOnce(value);
  }
  return nowSpy;
}

describe("GET /api/health/byok", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    ENV_STATE.byokHealthcheckKey = TEST_HEALTH_KEY;
    MOCK_CHECK_BYOK_VAULT_HEALTH.mockResolvedValue(undefined);
  });

  it("returns 503 when the operator token is not configured", async () => {
    ENV_STATE.byokHealthcheckKey = "";
    const { GET } = await import("../route");

    const res = await GET(byokHealthRequest({ "x-internal-key": TEST_HEALTH_KEY }));
    const body = await res.json();

    expect(res.status).toBe(503);
    expect(res.headers.get("Cache-Control")).toBe("no-store");
    expect(body).toEqual({
      error: "byok_health_not_configured",
      reason: "BYOK health check is not configured",
    });
    expect(MOCK_CHECK_BYOK_VAULT_HEALTH).not.toHaveBeenCalled();
  });

  it("requires an operator token", async () => {
    const { GET } = await import("../route");

    const res = await GET(byokHealthRequest());
    const body = await res.json();

    expect(res.status).toBe(401);
    expect(res.headers.get("Cache-Control")).toBe("no-store");
    expect(body).toEqual({
      error: "unauthorized",
      reason: "Authentication required",
    });
    expect(MOCK_CHECK_BYOK_VAULT_HEALTH).not.toHaveBeenCalled();
  });

  it("rejects invalid operator tokens", async () => {
    const { GET } = await import("../route");

    const res = await GET(byokHealthRequest({ "x-internal-key": "wrong" }));
    const body = await res.json();

    expect(res.status).toBe(403);
    expect(res.headers.get("Cache-Control")).toBe("no-store");
    expect(body).toEqual({
      error: "forbidden",
      reason: "Invalid BYOK health check key",
    });
    expect(MOCK_CHECK_BYOK_VAULT_HEALTH).not.toHaveBeenCalled();
  });

  it("returns a secret-free OK response when Vault health passes", async () => {
    const nowSpy = mockPerformanceNowSequence([10.25, 34.75]);
    const { GET } = await import("../route");

    try {
      const res = await GET(byokHealthRequest({ "x-internal-key": TEST_HEALTH_KEY }));
      const body = await res.json();

      expect(res.status).toBe(200);
      expect(res.headers.get("Cache-Control")).toBe("no-store");
      expect(body).toMatchObject({
        checks: { rpc: "ok", vault: "ok" },
        service: "tripsage-ai",
        status: "ok",
      });
      expect(JSON.stringify(body)).not.toContain(TEST_HEALTH_KEY);
      expect(MOCK_CHECK_BYOK_VAULT_HEALTH).toHaveBeenCalledTimes(1);
      expect(MOCK_WITH_TELEMETRY_SPAN).toHaveBeenCalledWith(
        "health.byok",
        {
          attributes: {
            "health.check": "byok",
            "health.component": "vault",
          },
        },
        expect.any(Function)
      );
      expect(MOCK_SPAN.setAttribute).toHaveBeenCalledWith("health.latency_ms", 24.5);
      expect(MOCK_SPAN.setAttribute).toHaveBeenCalledWith("health.status", "ok");
    } finally {
      nowSpy.mockRestore();
    }
  });

  it("accepts bearer tokens for external health monitors", async () => {
    const { GET } = await import("../route");

    const res = await GET(
      byokHealthRequest({ authorization: `Bearer ${TEST_HEALTH_KEY}` })
    );

    expect(res.status).toBe(200);
    expect(MOCK_CHECK_BYOK_VAULT_HEALTH).toHaveBeenCalledTimes(1);
  });

  it("returns VAULT_UNAVAILABLE when the Vault health RPC fails", async () => {
    const nowSpy = mockPerformanceNowSequence([40, 47.25]);
    MOCK_CHECK_BYOK_VAULT_HEALTH.mockRejectedValueOnce(new Error("secret leaked"));
    const { GET } = await import("../route");

    try {
      const res = await GET(byokHealthRequest({ "x-internal-key": TEST_HEALTH_KEY }));
      const body = await res.json();

      expect(res.status).toBe(503);
      expect(res.headers.get("Cache-Control")).toBe("no-store");
      expect(body).toEqual({
        error: "VAULT_UNAVAILABLE",
        reason: "BYOK Vault health check failed",
      });
      expect(JSON.stringify(body)).not.toContain("secret leaked");
      expect(MOCK_RECORD_TELEMETRY_EVENT).toHaveBeenCalledWith(
        "health.byok_failure",
        expect.objectContaining({
          attributes: expect.objectContaining({
            code: "VAULT_UNAVAILABLE",
            latency_ms: 7.25,
          }),
          level: "error",
        })
      );
      expect(MOCK_RECORD_ERROR_ON_SPAN).toHaveBeenCalledWith(
        MOCK_SPAN,
        expect.objectContaining({ message: "BYOK Vault health check failed" })
      );
      expect(MOCK_RECORD_ERROR_ON_SPAN.mock.calls[0]?.[1]?.message).not.toContain(
        "secret leaked"
      );
      expect(MOCK_SPAN.setAttribute).toHaveBeenCalledWith("health.latency_ms", 7.25);
      expect(MOCK_SPAN.setAttribute).toHaveBeenCalledWith("health.status", "error");
    } finally {
      nowSpy.mockRestore();
    }
  });
});
