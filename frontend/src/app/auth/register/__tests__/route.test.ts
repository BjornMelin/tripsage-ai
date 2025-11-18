/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const SIGN_UP_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({ error: null })) as MockInstance<
      (_args: {
        email: string;
        password: string;
        options: { data: Record<string, unknown>; emailRedirectTo: string };
      }) => Promise<{ error: Error | null }>
    >
);

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { signUp: SIGN_UP_MOCK },
  })),
}));

import { POST } from "../route";

describe("auth/register route", () => {
  beforeEach(() => {
    SIGN_UP_MOCK.mockClear();
  });

  it("creates a Supabase user and redirects to /register with status=check_email on success", async () => {
    const body = new URLSearchParams({
      acceptTerms: "on",
      confirmPassword: "StrongPassword!234",
      email: "user@example.com",
      firstName: "Test",
      lastName: "User",
      marketingOptIn: "on",
      password: "StrongPassword!234",
    }).toString();

    const req = createMockNextRequest({
      body,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      method: "POST",
      url: "https://app.example.com/auth/register",
    });

    const res = await POST(req);

    expect(SIGN_UP_MOCK).toHaveBeenCalledTimes(1);
    const args = SIGN_UP_MOCK.mock.calls[0]?.[0];
    expect(args).toBeDefined();
    expect(args.email).toBe("user@example.com");
    expect(args.password).toBe("StrongPassword!234");
    expect(args.options?.data).toMatchObject({
      email: "user@example.com",
      first_name: "Test",
      full_name: "Test User",
      last_name: "User",
      marketing_opt_in: true,
    });
    expect(typeof args.options?.emailRedirectTo).toBe("string");
    expect(args.options?.emailRedirectTo).toContain("/auth/confirm");

    expect(res.status).toBe(307);
    const location = res.headers.get("location");
    expect(location).toBe("https://app.example.com/register?status=check_email");
  });

  it("redirects back to /register with error when validation fails", async () => {
    const body = new URLSearchParams({
      acceptTerms: "on",
      confirmPassword: "different-password",
      email: "user@example.com",
      firstName: "Test",
      lastName: "User",
      password: "StrongPassword!234",
    }).toString();

    const req = createMockNextRequest({
      body,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      method: "POST",
      url: "https://app.example.com/auth/register",
    });

    const res = await POST(req);

    expect(SIGN_UP_MOCK).not.toHaveBeenCalled();
    expect(res.status).toBe(307);

    const location = res.headers.get("location");
    expect(location).toBeTruthy();
    const url = new URL(location ?? "");

    expect(url.pathname).toBe("/register");
    expect(url.searchParams.get("error")).toBeTruthy();
  });

  it("redirects back to /register with Supabase error message when sign-up fails", async () => {
    SIGN_UP_MOCK.mockResolvedValueOnce({ error: new Error("Email already in use") });

    const body = new URLSearchParams({
      acceptTerms: "on",
      confirmPassword: "StrongPassword!234",
      email: "user@example.com",
      firstName: "Test",
      lastName: "User",
      password: "StrongPassword!234",
    }).toString();

    const req = createMockNextRequest({
      body,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      method: "POST",
      url: "https://app.example.com/auth/register",
    });

    const res = await POST(req);

    expect(SIGN_UP_MOCK).toHaveBeenCalled();
    expect(res.status).toBe(307);

    const location = res.headers.get("location");
    expect(location).toBeTruthy();
    const url = new URL(location ?? "");

    expect(url.pathname).toBe("/register");
    expect(url.searchParams.get("error")).toBe("Email already in use");
  });
});
