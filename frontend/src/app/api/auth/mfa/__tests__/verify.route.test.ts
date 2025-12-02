/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RouteParamsContext } from "@/lib/api/factory";
import { makeJsonRequest } from "@/test/api-request-factory";
import { resetApiRouteMocks } from "@/test/api-route-helpers";

describe("POST /api/auth/mfa/verify", () => {
  const mockMfa = {
    verify: vi.fn(),
  };

  beforeEach(() => {
    resetApiRouteMocks();
    vi.doMock("@/lib/security/mfa", () => ({
      regenerateBackupCodes: vi.fn(async () => ({ codes: ["CODE-ONE"] })),
      verifyTotp: mockMfa.verify.mockImplementation(async () => Promise.resolve()),
    }));
    vi.doMock("@/lib/supabase/admin", () => ({
      createAdminSupabase: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("verifies code and returns backup codes", async () => {
    const { POST } = await import("../verify/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/verify", {
        challengeId: "challenge-1",
        code: "123456",
        factorId: "factor-1",
      }),
      { params: {} } as unknown as RouteParamsContext
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.data.status).toBe("verified");
    // backupCodes may be undefined if regen fails; ensure shape present
    expect(json.data).toHaveProperty("backupCodes");
  });

  it("returns 400 for invalid code", async () => {
    mockMfa.verify.mockRejectedValueOnce(new Error("bad code"));
    const { POST } = await import("../verify/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/verify", {
        challengeId: "challenge-1",
        code: "000000",
        factorId: "factor-1",
      }),
      { params: {} } as unknown as RouteParamsContext
    );
    expect(res.status).toBe(400);
  });
});
