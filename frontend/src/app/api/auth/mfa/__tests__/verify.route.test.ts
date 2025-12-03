/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  makeJsonRequest,
  resetApiRouteMocks,
} from "@/test/api-route-helpers";

const mockMfaVerify = vi.hoisted(() => vi.fn());
const mockRegenerate = vi.hoisted(() => vi.fn());
const mockGetAdminSupabase = vi.hoisted(() => vi.fn(() => ({})));

vi.mock("@/lib/security/mfa", () => ({
  regenerateBackupCodes: mockRegenerate,
  verifyTotp: mockMfaVerify,
}));

vi.mock("@/lib/supabase/admin", () => ({
  getAdminSupabase: mockGetAdminSupabase,
}));

describe("POST /api/auth/mfa/verify", () => {
  const ids = {
    challengeId: "22222222-2222-4222-8222-222222222222",
    factorId: "11111111-1111-4111-8111-111111111111",
  };

  beforeEach(() => {
    resetApiRouteMocks();
    mockRegenerate.mockReset();
    mockMfaVerify.mockReset();
    mockGetAdminSupabase.mockReset();
    mockRegenerate.mockResolvedValue({ codes: ["ABCDE-FGHIJ"], remaining: 10 });
    mockMfaVerify.mockResolvedValue({ isInitialEnrollment: true });
  });

  it("generates backup codes only on initial enrollment", async () => {
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
    mockMfaVerify.mockResolvedValueOnce({ isInitialEnrollment: false });
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
    mockMfaVerify.mockRejectedValueOnce(new Error("bad code"));
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
    mockMfaVerify.mockResolvedValueOnce({ isInitialEnrollment: true });
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
