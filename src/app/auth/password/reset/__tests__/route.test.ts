/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest } from "@/test/helpers/route";

const VERIFY_OTP_MOCK = vi.hoisted(
  () =>
    vi.fn(async (_args: unknown) => ({ error: null })) as MockInstance<
      (_args: unknown) => Promise<{ error: unknown | null }>
    >
);

const UPDATE_USER_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({ error: null })) as MockInstance<
      (_args: { password: string }) => Promise<{ error: unknown | null }>
    >
);

const CREATE_SUPABASE_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({
      auth: {
        updateUser: UPDATE_USER_MOCK,
        verifyOtp: VERIFY_OTP_MOCK,
      },
    })) as MockInstance<() => Promise<{ auth: Record<string, unknown> }>>
);

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE_MOCK,
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

describe("/auth/password/reset route", () => {
  beforeEach(() => {
    CREATE_SUPABASE_MOCK.mockClear();
    VERIFY_OTP_MOCK.mockClear();
    UPDATE_USER_MOCK.mockClear();
  });

  it("returns 413 when payload exceeds the size limit", async () => {
    const huge = "a".repeat(20_000);
    const req = createMockNextRequest({
      body: { newPassword: huge, token: huge },
      method: "POST",
      url: "http://localhost/auth/password/reset",
    });

    const res = await POST(req);
    expect(res.status).toBe(413);
    await expect(res.json()).resolves.toEqual({
      code: "PAYLOAD_TOO_LARGE",
      message: "Request body exceeds limit",
    });
  });

  it("returns 400 on validation error", async () => {
    const req = createMockNextRequest({
      body: { newPassword: "", token: "" },
      method: "POST",
      url: "http://localhost/auth/password/reset",
    });

    const res = await POST(req);
    expect(res.status).toBe(400);
    const body = (await res.json()) as { code?: string; errors?: unknown };
    expect(body.code).toBe("VALIDATION_ERROR");
    expect(body.errors).toBeDefined();
  });

  it("returns 400 when OTP verification fails", async () => {
    VERIFY_OTP_MOCK.mockResolvedValueOnce({
      error: { code: "bad_token", status: 400 },
    });

    const req = createMockNextRequest({
      body: { newPassword: "StrongPassword!234", token: "token-123" },
      method: "POST",
      url: "http://localhost/auth/password/reset",
    });

    const res = await POST(req);
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toMatchObject({ code: "RESET_FAILED" });
    expect(UPDATE_USER_MOCK).not.toHaveBeenCalled();
  });

  it("returns ok:true on success", async () => {
    VERIFY_OTP_MOCK.mockResolvedValueOnce({ error: null });
    UPDATE_USER_MOCK.mockResolvedValueOnce({ error: null });

    const req = createMockNextRequest({
      body: { newPassword: "StrongPassword!234", token: "token-123" },
      method: "POST",
      url: "http://localhost/auth/password/reset",
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
  });
});
