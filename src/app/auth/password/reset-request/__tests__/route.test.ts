/** @vitest-environment node */

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

vi.mock("botid/server", async () => {
  const { mockBotIdHumanResponse } = await import("@/test/mocks/botid");
  return {
    checkBotId: vi.fn(async () => mockBotIdHumanResponse),
  };
});

describe("POST /auth/password/reset-request", () => {
  afterEach(async () => {
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
    vi.unstubAllEnvs();
    __resetServerEnvCacheForTest();
  });

  it("fails closed when rate limiting infrastructure is unavailable", async () => {
    vi.stubEnv("APP_BASE_URL", "https://example.com");
    __resetServerEnvCacheForTest();
    const ResetPassword = vi.fn();
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setSupabaseFactoryForTests(async () =>
      unsafeCast({ auth: { resetPasswordForEmail: ResetPassword } })
    );
    setRateLimitFactoryForTests(() => Promise.reject(new Error("redis_down")));

    const { POST } = await import("../route");
    const req = new NextRequest("https://example.com/auth/password/reset-request", {
      body: JSON.stringify({ email: "test@example.com" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await POST(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(503);
    expect(await res.json()).toMatchObject({ error: "rate_limit_unavailable" });
    expect(ResetPassword).not.toHaveBeenCalled();
  });

  it("rate limits and calls supabase resetPasswordForEmail on valid input", async () => {
    vi.stubEnv("APP_BASE_URL", "https://app.example.com");
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com");
    __resetServerEnvCacheForTest();
    const ResetPassword = vi.fn(async () => ({ error: null }));
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setSupabaseFactoryForTests(async () =>
      unsafeCast({ auth: { resetPasswordForEmail: ResetPassword } })
    );
    setRateLimitFactoryForTests(async () => ({
      limit: 5,
      remaining: 4,
      reset: 0,
      success: true,
    }));

    const { POST } = await import("../route");
    const req = new NextRequest("https://example.com/auth/password/reset-request", {
      body: JSON.stringify({ email: "test@example.com" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await POST(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      message:
        "If the email exists, you will receive password reset instructions shortly.",
      ok: true,
    });
    expect(ResetPassword).toHaveBeenCalledWith("test@example.com", {
      redirectTo: "https://app.example.com/auth/reset-password",
    });
  });

  it("rejects bot traffic", async () => {
    vi.stubEnv("APP_BASE_URL", "https://example.com");
    __resetServerEnvCacheForTest();
    const ResetPassword = vi.fn(async () => ({ error: null }));
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setSupabaseFactoryForTests(async () =>
      unsafeCast({ auth: { resetPasswordForEmail: ResetPassword } })
    );
    setRateLimitFactoryForTests(async () => ({
      limit: 5,
      remaining: 4,
      reset: 0,
      success: true,
    }));

    const { checkBotId } = await import("botid/server");
    vi.mocked(checkBotId).mockResolvedValueOnce({
      bypassed: false,
      isBot: true,
      isHuman: false,
      isVerifiedBot: false,
    });

    const { POST } = await import("../route");
    const req = new NextRequest("https://example.com/auth/password/reset-request", {
      body: JSON.stringify({ email: "test@example.com" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await POST(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(403);
    expect(await res.json()).toMatchObject({ error: "bot_detected" });
    expect(ResetPassword).not.toHaveBeenCalled();
  });

  it("rejects requests from untrusted origins", async () => {
    vi.stubEnv("APP_BASE_URL", "https://app.example.com");
    __resetServerEnvCacheForTest();
    const ResetPassword = vi.fn(async () => ({ error: null }));
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setSupabaseFactoryForTests(async () =>
      unsafeCast({ auth: { resetPasswordForEmail: ResetPassword } })
    );
    setRateLimitFactoryForTests(async () => ({
      limit: 5,
      remaining: 4,
      reset: 0,
      success: true,
    }));

    const { POST } = await import("../route");
    const req = new NextRequest(
      "https://evil.example.com/auth/password/reset-request",
      {
        body: JSON.stringify({ email: "test@example.com" }),
        headers: { "content-type": "application/json" },
        method: "POST",
      }
    );

    const res = await POST(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({
      code: "INVALID_HOST",
      message: "Invalid request host",
    });
    expect(ResetPassword).not.toHaveBeenCalled();
  });

  it("returns a generic success response when Supabase reports an error", async () => {
    vi.stubEnv("APP_BASE_URL", "https://example.com");
    __resetServerEnvCacheForTest();
    const ResetPassword = vi.fn(async () => ({
      error: { code: "user_not_found", message: "User not found", status: 400 },
    }));
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setSupabaseFactoryForTests(async () =>
      unsafeCast({ auth: { resetPasswordForEmail: ResetPassword } })
    );
    setRateLimitFactoryForTests(async () => ({
      limit: 5,
      remaining: 4,
      reset: 0,
      success: true,
    }));

    const { POST } = await import("../route");
    const req = new NextRequest("https://example.com/auth/password/reset-request", {
      body: JSON.stringify({ email: "test@example.com" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await POST(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      message:
        "If the email exists, you will receive password reset instructions shortly.",
      ok: true,
    });
  });

  it("returns a structured error for malformed JSON", async () => {
    vi.stubEnv("APP_BASE_URL", "https://example.com");
    __resetServerEnvCacheForTest();
    const ResetPassword = vi.fn(async () => ({ error: null }));
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setSupabaseFactoryForTests(async () =>
      unsafeCast({ auth: { resetPasswordForEmail: ResetPassword } })
    );
    setRateLimitFactoryForTests(async () => ({
      limit: 5,
      remaining: 4,
      reset: 0,
      success: true,
    }));

    const { POST } = await import("../route");
    const req = new NextRequest("https://example.com/auth/password/reset-request", {
      body: "{",
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await POST(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({
      code: "BAD_REQUEST",
      message: "Malformed JSON",
    });
    expect(ResetPassword).not.toHaveBeenCalled();
  });
});
