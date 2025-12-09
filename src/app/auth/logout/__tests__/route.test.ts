/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/helpers/route";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const SIGN_OUT_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({ error: null })) as MockInstance<
      () => Promise<{ error: Error | null }>
    >
);

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { signOut: SIGN_OUT_MOCK },
  })),
}));

import { GET, POST } from "../route";

describe("auth/logout route", () => {
  beforeEach(() => {
    SIGN_OUT_MOCK.mockClear();
  });

  it("POST /auth/logout signs out and returns success JSON when Supabase signOut succeeds", async () => {
    const req = createMockNextRequest({
      method: "POST",
      url: "https://app.example.com/auth/logout",
    });

    const res = await POST(req);

    expect(SIGN_OUT_MOCK).toHaveBeenCalledTimes(1);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ success: true });
  });

  it("POST /auth/logout returns 500 with error payload when Supabase signOut fails", async () => {
    SIGN_OUT_MOCK.mockResolvedValueOnce({ error: new Error("signout failed") });

    const req = createMockNextRequest({
      method: "POST",
      url: "https://app.example.com/auth/logout",
    });

    const res = await POST(req);

    expect(SIGN_OUT_MOCK).toHaveBeenCalledTimes(1);
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body).toEqual({
      error: "logout_failed",
      message: "signout failed",
    });
  });

  it("GET /auth/logout signs out and redirects to /login", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/logout",
    });

    const res = await GET(req);

    expect(SIGN_OUT_MOCK).toHaveBeenCalledTimes(1);
    expect(res.status).toBe(307);
    const location = res.headers.get("location");
    expect(location).toBe("https://app.example.com/login");
  });
});
