/** @vitest-environment node */

import { NextRequest } from "next/server";
import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const REQUIRE_USER_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({
      supabase: {
        auth: { resend: vi.fn(async () => ({ error: null })) },
      },
      user: { email: "user@example.com" },
    })) as MockInstance<
      (_args: { redirectTo: string }) => Promise<{
        supabase: { auth: { resend: MockInstance } };
        user: { email?: string };
      }>
    >
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
    REQUIRE_USER_MOCK.mockResolvedValueOnce({
      supabase: { auth: { resend: vi.fn(async () => ({ error: null })) } },
      user: { email: undefined },
    });

    const res = await POST(new NextRequest("http://localhost/auth/email/resend"));
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toMatchObject({ code: "EMAIL_REQUIRED" });
  });

  it("returns 400 when resend fails", async () => {
    const resend = vi.fn(async () => ({ error: { message: "Resend failed" } }));
    REQUIRE_USER_MOCK.mockResolvedValueOnce({
      supabase: { auth: { resend } },
      user: { email: "user@example.com" },
    });

    const res = await POST(new NextRequest("http://localhost/auth/email/resend"));
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toEqual({
      code: "RESEND_FAILED",
      message: "Resend failed",
    });
  });

  it("returns ok:true on success", async () => {
    const resend = vi.fn(async () => ({ error: null }));
    REQUIRE_USER_MOCK.mockResolvedValueOnce({
      supabase: { auth: { resend } },
      user: { email: "user@example.com" },
    });

    const res = await POST(new NextRequest("http://localhost/auth/email/resend"));
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
  });
});
