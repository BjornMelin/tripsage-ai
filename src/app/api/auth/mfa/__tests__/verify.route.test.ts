/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

const mockMfaVerify = vi.hoisted(() => vi.fn());
const mockRegenerate = vi.hoisted(() => vi.fn());
const mockFrom = vi.hoisted(() => vi.fn());
const mockGetAdminSupabase = vi.hoisted(() =>
  vi.fn(() => ({
    from: mockFrom,
  }))
);

const mockBackupCodeCount = (count: number) => {
  const mockIs = vi.fn(() => ({ count, error: undefined }));
  const mockEq = vi.fn(() => ({ is: mockIs }));
  const mockSelect = vi.fn(() => ({ eq: mockEq }));
  mockFrom.mockReturnValue({ select: mockSelect });
};

vi.mock("@/lib/security/mfa", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/security/mfa")>("@/lib/security/mfa");
  return {
    ...actual,
    regenerateBackupCodes: mockRegenerate,
    verifyTotp: mockMfaVerify,
  };
});

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

    mockBackupCodeCount(0); // user has no existing backup codes by default
  });

  it("generates backup codes only on initial enrollment when user has no existing codes", async () => {
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
    mockBackupCodeCount(5); // user already has backup codes
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

  it("returns 401 when user id is missing during initial enrollment", async () => {
    mockMfaVerify.mockResolvedValueOnce({ isInitialEnrollment: true });
    mockApiRouteAuthUser({ id: undefined as unknown as string });

    const { POST } = await import("../verify/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/verify", {
        challengeId: ids.challengeId,
        code: "123456",
        factorId: ids.factorId,
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(401);
    const json = await res.json();
    // unauthorizedResponse() returns "unauthorized" for consistency with other auth errors
    expect(json.error).toBe("unauthorized");
    expect(mockRegenerate).not.toHaveBeenCalled();
  });

  it("returns 400 for invalid code", async () => {
    mockMfaVerify.mockRejectedValueOnce({ code: "invalid_or_expired_code" });
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
    const json = await res.json();
    expect(json.error).toBe("invalid_or_expired_code");
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

  it("returns 500 when backup code count query fails during initial enrollment", async () => {
    const mockIs = vi.fn(() => ({ count: null, error: { message: "db_error" } }));
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

    expect(res.status).toBe(500);
    const json = await res.json();
    expect(json.error).toBe("failed_to_fetch_backup_codes");
    expect(mockRegenerate).not.toHaveBeenCalled();
  });
});
