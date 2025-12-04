/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/api-route-helpers";

const mockMfaVerify = vi.hoisted(() => vi.fn());
const mockRegenerate = vi.hoisted(() => vi.fn());
const mockFrom = vi.hoisted(() => vi.fn());
const mockGetAdminSupabase = vi.hoisted(() =>
  vi.fn(() => ({
    from: mockFrom,
  }))
);

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
    mockGetAdminSupabase.mockClear();
    mockFrom.mockReset();
    mockRegenerate.mockResolvedValue({ codes: ["ABCDE-FGHIJ"] });
    mockMfaVerify.mockResolvedValue({ isInitialEnrollment: true });

    // Mock backup codes check: return 0 existing codes (user has no backup codes)
    const mockIs = vi.fn(() => ({ count: 0 }));
    const mockEq = vi.fn(() => ({ is: mockIs }));
    const mockSelect = vi.fn(() => ({ eq: mockEq }));
    mockFrom.mockReturnValue({ select: mockSelect });
  });

  it("generates backup codes only on initial enrollment when user has no existing codes", async () => {
    // Mock: user has no existing backup codes (count: 0)
    const mockIs = vi.fn(() => ({ count: 0 }));
    const mockEq = vi.fn(() => ({ is: mockIs }));
    const mockSelect = vi.fn(() => ({ eq: mockEq }));
    mockFrom.mockReturnValue({ select: mockSelect });

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

  it("does not generate backup codes if user already has backup codes even if isInitialEnrollment is true", async () => {
    // Mock: user already has backup codes (count: 5)
    const mockIs = vi.fn(() => ({ count: 5 }));
    const mockEq = vi.fn(() => ({ is: mockIs }));
    const mockSelect = vi.fn(() => ({ eq: mockEq }));
    mockFrom.mockReturnValue({ select: mockSelect });

    mockMfaVerify.mockResolvedValueOnce({ isInitialEnrollment: true });
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

  it("returns 401 when user is not authenticated", async () => {
    mockMfaVerify.mockResolvedValueOnce({ isInitialEnrollment: true });
    mockApiRouteAuthUser(null);

    const { POST } = await import("../verify/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/verify", {
        challengeId: ids.challengeId,
        code: "123456",
        factorId: ids.factorId,
      }),
      createRouteParamsContext()
    );

    // withApiGuards auth check returns "unauthorized" before handler runs
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.error).toBe("unauthorized");
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
