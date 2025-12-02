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
  const mockRegenerate = vi.fn();

  beforeEach(() => {
    resetApiRouteMocks();
    mockRegenerate.mockResolvedValue({ codes: ["ABCDE-FGHIJ"], remaining: 10 });
    vi.doMock("@/lib/security/mfa", () => ({
      regenerateBackupCodes: mockRegenerate,
      verifyTotp: mockMfa.verify.mockResolvedValue({ isInitialEnrollment: true }),
    }));
    vi.doMock("@/lib/supabase/admin", () => ({
      getAdminSupabase: vi.fn(() => ({})),
    }));
  });

  afterEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("generates backup codes only on initial enrollment", async () => {
    mockMfa.verify.mockResolvedValueOnce({ isInitialEnrollment: true });
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
    expect(json.data.backupCodes).toEqual(["ABCDE-FGHIJ"]);
    expect(mockRegenerate).toHaveBeenCalled();
  });

  it("does not generate backup codes on subsequent challenges", async () => {
    mockMfa.verify.mockResolvedValueOnce({ isInitialEnrollment: false });
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
    expect(json.data.backupCodes).toBeUndefined();
    expect(mockRegenerate).not.toHaveBeenCalled();
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

  it("continues when backup code regeneration fails on initial enrollment", async () => {
    mockMfa.verify.mockResolvedValueOnce({ isInitialEnrollment: true });
    mockRegenerate.mockRejectedValueOnce(new Error("regen_failed"));
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
    expect(json.data.backupCodes).toBeUndefined();
  });
});
