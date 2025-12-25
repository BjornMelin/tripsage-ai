/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthContext } from "@/lib/auth/server";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

type RequireUserFn = (options?: { redirectTo?: string }) => Promise<AuthContext>;

const REQUIRE_USER_MOCK = vi.hoisted(() =>
  vi.fn<RequireUserFn>(async () =>
    unsafeCast<AuthContext>({
      supabase: {
        auth: { resend: vi.fn(async () => ({ error: null })) },
      },
      user: { email: "user@example.com" },
    })
  )
);

vi.mock("@/lib/auth/server", () => ({
  requireUser: REQUIRE_USER_MOCK,
}));

import { POST } from "../route";

describe("/auth/email/resend route", () => {
  beforeEach(() => {
    REQUIRE_USER_MOCK.mockClear();
  });

  it("returns 400 when user email is missing", async () => {
    const resend = vi.fn(async () => ({ error: null }));
    REQUIRE_USER_MOCK.mockResolvedValueOnce(
      unsafeCast<AuthContext>({
        supabase: { auth: { resend } },
        user: { email: undefined },
      })
    );

    const res = await POST(new NextRequest("http://localhost/auth/email/resend"));
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toMatchObject({ code: "EMAIL_REQUIRED" });
    expect(resend).not.toHaveBeenCalled();
  });

  it("returns 400 when resend fails", async () => {
    const resend = vi.fn(async () => ({ error: { message: "Resend failed" } }));
    REQUIRE_USER_MOCK.mockResolvedValueOnce(
      unsafeCast<AuthContext>({
        supabase: { auth: { resend } },
        user: { email: "user@example.com" },
      })
    );

    const res = await POST(new NextRequest("http://localhost/auth/email/resend"));
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toEqual({
      code: "RESEND_FAILED",
      message: "Resend failed",
    });
    expect(resend).toHaveBeenCalledTimes(1);
    expect(resend).toHaveBeenCalledWith({ email: "user@example.com", type: "signup" });
  });

  it("returns ok:true on success", async () => {
    const resend = vi.fn(async () => ({ error: null }));
    REQUIRE_USER_MOCK.mockResolvedValueOnce(
      unsafeCast<AuthContext>({
        supabase: { auth: { resend } },
        user: { email: "user@example.com" },
      })
    );

    const res = await POST(new NextRequest("http://localhost/auth/email/resend"));
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
    expect(resend).toHaveBeenCalledTimes(1);
    expect(resend).toHaveBeenCalledWith({ email: "user@example.com", type: "signup" });
  });
});
