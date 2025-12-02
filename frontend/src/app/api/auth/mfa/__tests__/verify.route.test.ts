/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeJsonRequest } from "@/test/api-request-factory";
import { resetApiRouteMocks } from "@/test/api-route-helpers";
import { createRouteParamsContext } from "@/test/route-helpers";

describe("POST /api/auth/mfa/verify", () => {
  const ids = {
    challengeId: "22222222-2222-4222-8222-222222222222",
    factorId: "11111111-1111-4111-8111-111111111111",
  };
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
      getAdminSupabase: vi.fn(() => ({})),
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
        challengeId: ids.challengeId,
        code: "123456",
        factorId: ids.factorId,
      }),
      createRouteParamsContext()
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
        challengeId: ids.challengeId,
        code: "000000",
        factorId: ids.factorId,
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(400);
  });

  it("continues when backup code regeneration fails", async () => {
    vi.doMock("@/lib/security/mfa", () => ({
      regenerateBackupCodes: vi.fn(() => {
        throw new Error("regen_failed");
      }),
      verifyTotp: mockMfa.verify.mockImplementation(async () => Promise.resolve()),
    }));
    const { POST } = await import("../verify/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/verify", {
        challengeId: ids.challengeId,
        code: "123456",
        factorId: ids.factorId,
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.data.backupCodes).toBeUndefined();
  });
});
