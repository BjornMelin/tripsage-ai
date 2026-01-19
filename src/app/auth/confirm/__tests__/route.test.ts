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

const VERIFY_MOCK = vi.hoisted(
  () =>
    vi.fn(async (_args: { token_hash: string; type: string }) => ({
      error: null,
    })) as MockInstance<
      (_args: { token_hash: string; type: string }) => Promise<{ error: Error | null }>
    >
);

const EXCHANGE_MOCK = vi.hoisted(
  () =>
    vi.fn(() => Promise.resolve({ error: null })) as MockInstance<
      (code: string) => Promise<{ error: Error | null }>
    >
);

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { exchangeCodeForSession: EXCHANGE_MOCK, verifyOtp: VERIFY_MOCK },
  })),
}));

// Mock next/navigation redirect helper
const REDIRECT_MOCK = vi.hoisted(
  () => vi.fn() as MockInstance<(...args: string[]) => never>
);
vi.mock("next/navigation", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    redirect: REDIRECT_MOCK,
  };
});

import { GET } from "../route";

describe("auth/confirm route", () => {
  beforeEach(() => {
    VERIFY_MOCK.mockClear();
    EXCHANGE_MOCK.mockClear();
    REDIRECT_MOCK.mockClear();
  });

  it("verifies token and redirects to next path", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%2Fdashboard%2Ftrips%3Ftab%3Dmine",
    });
    await GET(req);
    expect(VERIFY_MOCK).toHaveBeenCalledWith({ token_hash: "thash", type: "email" });
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/dashboard/trips?tab=mine");
  });

  it("exchanges code for session and redirects to next path", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/confirm?code=abc123&next=%2Fdashboard",
    });
    await GET(req);
    expect(EXCHANGE_MOCK).toHaveBeenCalledWith("abc123");
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to login when Supabase provides an error payload", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/confirm?error=access_denied&error_code=otp_expired&next=%2Fdashboard",
    });
    await GET(req);
    expect(REDIRECT_MOCK).toHaveBeenCalledWith(
      "/login?error=auth_confirm_failed&next=%2Fdashboard&error_code=otp_expired"
    );
  });

  it.each([
    [
      "//evil",
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=//evil",
    ],
    [
      "%2F%2Fevil",
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%2F%2Fevil",
    ],
    [
      "%252F%252Fevil",
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%252F%252Fevil",
    ],
    [
      "\\\\evil",
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%5C%5Cevil",
    ],
    [
      "http://evil.example",
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=http://evil.example",
    ],
    [
      "/dashboard\\r\\n",
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%2Fdashboard%0D%0A",
    ],
  ])("rejects open redirect next=%s", async (_label, url) => {
    const req = createMockNextRequest({ method: "GET", url });
    await GET(req);
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/dashboard");
  });

  it("falls back to safe default when next is internal but not allowlisted", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%2Fwelcome",
    });
    await GET(req);
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to error on verify failure", async () => {
    VERIFY_MOCK.mockResolvedValueOnce({ error: new Error("invalid") });
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/confirm?token_hash=bad&type=email",
    });
    await GET(req);
    expect(REDIRECT_MOCK).toHaveBeenCalledWith(
      "/login?error=auth_confirm_failed&next=%2Fdashboard"
    );
  });
});
