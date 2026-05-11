/** @vitest-environment node */

import type { AuthTokenResponsePassword, UserResponse } from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  apiRouteRateLimitSpy,
  createRouteParamsContext,
  enableApiRouteRateLimit,
  getApiRouteSupabaseMock,
  makeJsonRequest,
  mockApiRouteAuthUser,
  mockApiRouteRateLimitOnce,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

vi.mock("@/lib/telemetry/degraded-mode", () => ({
  emitOperationalAlertOncePerWindow: vi.fn(),
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  }),
}));

import { POST } from "../route";

describe("/auth/password/change route", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    enableApiRouteRateLimit();
  });

  it("returns 413 when payload exceeds the size limit", async () => {
    const huge = "a".repeat(10_000);
    const req = makeJsonRequest("/auth/password/change", {
      confirmPassword: huge,
      currentPassword: huge,
      newPassword: huge,
    });

    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(413);
    await expect(res.json()).resolves.toEqual({
      code: "PAYLOAD_TOO_LARGE",
      message: "Request body exceeds limit",
    });
  });

  it("returns 403 when MFA is required to verify current password", async () => {
    const signInWithPassword = vi.fn(async (_credentials: unknown) => ({
      data: { session: null, user: null },
      error: { code: "mfa_required", message: "mfa required", status: 403 },
    }));
    const updateUser = vi.fn(async () =>
      unsafeCast<UserResponse>({ data: { user: null }, error: null })
    );
    const supabase = getApiRouteSupabaseMock();
    vi.spyOn(supabase.auth, "signInWithPassword").mockImplementation(
      async (credentials) =>
        unsafeCast<AuthTokenResponsePassword>(await signInWithPassword(credentials))
    );
    vi.spyOn(supabase.auth, "updateUser").mockImplementation(updateUser);

    const req = makeJsonRequest("/auth/password/change", {
      confirmPassword: "StrongPassword!234",
      currentPassword: "CurrentPassword!234",
      newPassword: "StrongPassword!234",
    });

    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(403);
    await expect(res.json()).resolves.toMatchObject({ code: "mfa_required" });
  });

  it("returns ok:true when password is changed successfully with the store payload", async () => {
    const signInWithPassword = vi.fn(async () =>
      unsafeCast<AuthTokenResponsePassword>({
        data: { session: null, user: null },
        error: null,
      })
    );
    const updateUser = vi.fn(async () =>
      unsafeCast<UserResponse>({ data: { user: null }, error: null })
    );
    const supabase = getApiRouteSupabaseMock();
    vi.spyOn(supabase.auth, "signInWithPassword").mockImplementation(
      signInWithPassword
    );
    vi.spyOn(supabase.auth, "updateUser").mockImplementation(updateUser);

    const req = makeJsonRequest("/auth/password/change", {
      currentPassword: "CurrentPassword!234",
      newPassword: "StrongPassword!234",
    });

    const res = await POST(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
    expect(signInWithPassword).toHaveBeenCalledWith({
      email: "test@example.com",
      password: "CurrentPassword!234",
    });
    expect(updateUser).toHaveBeenCalledWith({ password: "StrongPassword!234" });
  });

  it("rate-limits password change attempts before body validation", async () => {
    mockApiRouteRateLimitOnce({
      limit: 3,
      remaining: 0,
      reset: Date.now() + 60_000,
      success: false,
    });

    const req = makeJsonRequest("/auth/password/change", {
      confirmPassword: "short",
      currentPassword: "short",
      newPassword: "short",
    });

    const res = await POST(req, createRouteParamsContext());

    expect(res.status).toBe(429);
    expect(apiRouteRateLimitSpy).toHaveBeenCalledWith(
      "auth:password:change",
      expect.stringMatching(/^user:/)
    );
  });

  it("rejects unauthenticated password changes before parsing the body", async () => {
    mockApiRouteAuthUser(null);

    const req = makeJsonRequest("/auth/password/change", {
      confirmPassword: "StrongPassword!234",
      currentPassword: "CurrentPassword!234",
      newPassword: "StrongPassword!234",
    });

    const res = await POST(req, createRouteParamsContext());

    expect(res.status).toBe(401);
  });
});
