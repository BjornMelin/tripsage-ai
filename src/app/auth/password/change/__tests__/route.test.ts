/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest } from "@/test/helpers/route";

const REQUIRE_USER_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({
      supabase: {
        auth: {
          signInWithPassword: vi.fn(async () => ({ error: null })),
          updateUser: vi.fn(async () => ({ error: null })),
        },
      },
      user: { email: "user@example.com" },
    })) as MockInstance<
      (_args: { redirectTo: string }) => Promise<{
        supabase: {
          auth: {
            signInWithPassword: MockInstance;
            updateUser: MockInstance;
          };
        };
        user: { email?: string };
      }>
    >
);

vi.mock("@/lib/auth/server", () => ({
  requireUser: REQUIRE_USER_MOCK,
}));

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
    REQUIRE_USER_MOCK.mockClear();
  });

  it("returns 413 when payload exceeds the size limit", async () => {
    const huge = "a".repeat(10_000);
    const req = createMockNextRequest({
      body: {
        confirmPassword: huge,
        currentPassword: huge,
        newPassword: huge,
      },
      method: "POST",
      url: "http://localhost/auth/password/change",
    });

    const res = await POST(req);
    expect(res.status).toBe(413);
    await expect(res.json()).resolves.toEqual({
      code: "PAYLOAD_TOO_LARGE",
      message: "Request body exceeds limit",
    });
  });

  it("returns 403 when MFA is required to verify current password", async () => {
    const signInWithPassword = vi.fn(async () => ({
      error: { code: "mfa_required", message: "mfa required", status: 403 },
    }));
    const updateUser = vi.fn(async () => ({ error: null }));

    REQUIRE_USER_MOCK.mockResolvedValueOnce({
      supabase: { auth: { signInWithPassword, updateUser } },
      user: { email: "user@example.com" },
    });

    const req = createMockNextRequest({
      body: {
        confirmPassword: "StrongPassword!234",
        currentPassword: "CurrentPassword!234",
        newPassword: "StrongPassword!234",
      },
      method: "POST",
      url: "http://localhost/auth/password/change",
    });

    const res = await POST(req);
    expect(res.status).toBe(403);
    await expect(res.json()).resolves.toMatchObject({ code: "mfa_required" });
  });

  it("returns ok:true when password is changed successfully", async () => {
    const signInWithPassword = vi.fn(async () => ({ error: null }));
    const updateUser = vi.fn(async () => ({ error: null }));

    REQUIRE_USER_MOCK.mockResolvedValueOnce({
      supabase: { auth: { signInWithPassword, updateUser } },
      user: { email: "user@example.com" },
    });

    const req = createMockNextRequest({
      body: {
        confirmPassword: "StrongPassword!234",
        currentPassword: "CurrentPassword!234",
        newPassword: "StrongPassword!234",
      },
      method: "POST",
      url: "http://localhost/auth/password/change",
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
  });
});
