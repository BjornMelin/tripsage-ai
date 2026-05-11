/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  disableApiRouteRateLimit,
  enableApiRouteRateLimit,
  makeJsonRequest,
  mockApiRouteRateLimitOnce,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

const LOGGER_WARN = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: LOGGER_WARN,
  }),
}));

import { POST } from "../route";

describe("/api/security/csp-report", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    enableApiRouteRateLimit();
    LOGGER_WARN.mockClear();
  });

  it("accepts CSP report-only violation reports without echoing payload", async () => {
    const req = makeJsonRequest("/api/security/csp-report", {
      "csp-report": {
        "blocked-uri": "inline",
        disposition: "report",
        "document-uri":
          "https://example.com/auth/callback?token_hash=secret-token&next=/dashboard",
        "effective-directive": "script-src",
      },
    });

    const res = await POST(req, createRouteParamsContext());

    expect(res.status).toBe(204);
    expect(await res.text()).toBe("");
    expect(LOGGER_WARN).toHaveBeenCalledWith("csp_violation_report", {
      blockedUri: "inline",
      disposition: "report",
      documentUri: "https://example.com/auth/callback",
      effectiveDirective: "script-src",
    });
    expect(JSON.stringify(LOGGER_WARN.mock.calls)).not.toContain("secret-token");
  });

  it("rate-limits report ingestion", async () => {
    mockApiRouteRateLimitOnce({
      limit: 120,
      remaining: 0,
      reset: Date.now() + 60_000,
      success: false,
    });

    const req = makeJsonRequest("/api/security/csp-report", {
      "csp-report": {
        "blocked-uri": "inline",
      },
    });

    const res = await POST(req, createRouteParamsContext());

    expect(res.status).toBe(429);
  });

  it("fails closed when report rate limiting is unavailable", async () => {
    disableApiRouteRateLimit();

    const req = makeJsonRequest("/api/security/csp-report", {
      "csp-report": {
        "blocked-uri": "inline",
      },
    });

    const res = await POST(req, createRouteParamsContext());

    expect(res.status).toBe(503);
  });

  it("drops invalid non-URI telemetry fields", async () => {
    const req = makeJsonRequest("/api/security/csp-report", {
      "csp-report": {
        disposition: "report".repeat(2000),
        "effective-directive": "script-src;token=secret",
      },
    });

    const res = await POST(req, createRouteParamsContext());

    expect(res.status).toBe(204);
    expect(LOGGER_WARN).toHaveBeenCalledWith(
      "csp_violation_report",
      expect.objectContaining({
        disposition: null,
        effectiveDirective: null,
      })
    );
    expect(JSON.stringify(LOGGER_WARN.mock.calls)).not.toContain("secret");
  });
});
