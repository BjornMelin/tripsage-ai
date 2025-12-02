/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeJsonRequest } from "@/test/api-request-factory";
import { resetApiRouteMocks } from "@/test/api-route-helpers";
import { createRouteParamsContext } from "@/test/route-helpers";

describe("POST /api/auth/mfa/setup", () => {
  const mockMfa = {
    startTotpEnrollment: vi.fn(),
  };

  beforeEach(() => {
    resetApiRouteMocks();
    vi.doMock("@/lib/supabase/admin", () => ({
      getAdminSupabase: vi.fn(() => ({ from: vi.fn() })),
    }));
    vi.doMock("@/lib/security/mfa", () => ({
      startTotpEnrollment: mockMfa.startTotpEnrollment.mockImplementation(async () => ({
        challengeId: "challenge-1",
        expiresAt: new Date(Date.now() + 900_000).toISOString(),
        factorId: "factor-1",
        issuedAt: new Date().toISOString(),
        qrCode: "data:image/png;base64,TEST",
        secret: "SECRET-KEY",
        ttlSeconds: 900,
        uri: "otpauth://...",
      })),
    }));
  });

  afterEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("returns enrollment payload without secret and with ttlSeconds", async () => {
    const { POST } = await import("../setup/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/setup", {}),
      createRouteParamsContext()
    );
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.data.factorId).toBe("factor-1");
    expect(json.data.challengeId).toBe("challenge-1");
    expect(json.data.secret).toBeUndefined();
    expect(typeof json.data.ttlSeconds).toBe("number");
    expect(json.data.ttlSeconds).toBeGreaterThan(0);
  });

  it("handles enroll failure", async () => {
    mockMfa.startTotpEnrollment.mockRejectedValueOnce(new Error("boom"));
    const { POST } = await import("../setup/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/setup", {}),
      createRouteParamsContext()
    );
    expect(res.status).toBe(500);
    const json = await res.json();
    expect(json.error).toBe("mfa_setup_failed");
  });
});
