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

const VERIFY_MOCK = vi.hoisted(
  () =>
    vi.fn(async (_args: { token_hash: string; type: string }) => ({
      error: null,
    })) as MockInstance<
      (_args: { token_hash: string; type: string }) => Promise<{ error: Error | null }>
    >
);

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({ auth: { verifyOtp: VERIFY_MOCK } })),
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
    REDIRECT_MOCK.mockClear();
  });

  it("verifies token and redirects to next path", async () => {
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%2F",
    });
    await GET(req);
    expect(VERIFY_MOCK).toHaveBeenCalledWith({ token_hash: "thash", type: "email" });
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/");
  });

  it("redirects to error on verify failure", async () => {
    VERIFY_MOCK.mockResolvedValueOnce({ error: new Error("invalid") });
    const req = createMockNextRequest({
      method: "GET",
      url: "https://app.example.com/auth/confirm?token_hash=bad&type=email",
    });
    await GET(req);
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/error");
  });
});
