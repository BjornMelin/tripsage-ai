import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const SIGN_IN_MOCK: MockInstance<
  (_args: { email: string; password: string }) => Promise<{ error: Error | null }>
> = vi.fn(async () => ({ error: null }));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { signInWithPassword: SIGN_IN_MOCK },
  })),
}));

import { POST } from "../route";

describe("auth/login route", () => {
  beforeEach(() => {
    SIGN_IN_MOCK.mockClear();
  });

  it("signs in with Supabase and redirects to the provided path when credentials are valid", async () => {
    const body = new URLSearchParams({
      email: "user@example.com",
      password: "StrongPassword!234",
      redirectTo: "/dashboard",
    }).toString();

    const req = createMockNextRequest({
      body,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      method: "POST",
      url: "https://app.example.com/auth/login",
    });

    const res = await POST(req);

    expect(SIGN_IN_MOCK).toHaveBeenCalledWith({
      email: "user@example.com",
      password: "StrongPassword!234",
    });

    expect(res.status).toBe(307);
    const location = res.headers.get("location");
    expect(location).toBe("https://app.example.com/dashboard");
  });

  it("redirects back to /login with error and preserves redirectTo when validation fails", async () => {
    const body = new URLSearchParams({
      email: "not-an-email",
      password: "",
      redirectTo: "/protected",
    }).toString();

    const req = createMockNextRequest({
      body,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      method: "POST",
      url: "https://app.example.com/auth/login",
    });

    const res = await POST(req);

    expect(SIGN_IN_MOCK).not.toHaveBeenCalled();
    expect(res.status).toBe(307);

    const location = res.headers.get("location");
    expect(location).toBeTruthy();
    const url = new URL(location ?? "");

    expect(url.pathname).toBe("/login");
    expect(url.searchParams.get("error")).toBeTruthy();
    expect(url.searchParams.get("from")).toBe("/protected");
    expect(url.searchParams.get("next")).toBe("/protected");
  });

  it("redirects back to /login with Supabase error message when sign-in fails", async () => {
    SIGN_IN_MOCK.mockResolvedValueOnce({ error: new Error("Bad credentials") });

    const body = new URLSearchParams({
      email: "user@example.com",
      password: "wrong",
      redirectTo: "/dashboard",
    }).toString();

    const req = createMockNextRequest({
      body,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      method: "POST",
      url: "https://app.example.com/auth/login",
    });

    const res = await POST(req);

    expect(SIGN_IN_MOCK).toHaveBeenCalled();
    expect(res.status).toBe(307);

    const location = res.headers.get("location");
    expect(location).toBeTruthy();
    const url = new URL(location ?? "");

    expect(url.pathname).toBe("/login");
    expect(url.searchParams.get("error")).toBe("Bad credentials");
    expect(url.searchParams.get("from")).toBe("/dashboard");
    expect(url.searchParams.get("next")).toBe("/dashboard");
  });
});
