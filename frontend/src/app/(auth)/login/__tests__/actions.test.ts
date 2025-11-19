/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock next/navigation redirect BEFORE any imports that use it
const mockRedirect = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({
  redirect: mockRedirect,
}));

// Mock Supabase server client
const SIGN_IN_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({ error: null })) as MockInstance<
      () => Promise<{ error: Error | null }>
    >
);

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { signInWithPassword: SIGN_IN_MOCK },
  })),
}));

import { loginAction } from "../actions";

describe("loginAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SIGN_IN_MOCK.mockResolvedValue({ error: null });
    mockRedirect.mockClear();
  });

  it("redirects to sanitized redirectTo path on successful login", async () => {
    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "validpassword");
    formData.append("redirectTo", "/dashboard");
    formData.append("next", "/dashboard");

    const result = await loginAction({ success: false }, formData);

    // Should not return - should redirect instead
    expect(result).toBeUndefined();
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
    expect(SIGN_IN_MOCK).toHaveBeenCalledWith({
      email: "user@example.com",
      password: "validpassword",
    });
  });

  it("sanitizes unsafe redirect paths to /dashboard", async () => {
    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "validpassword");
    formData.append("redirectTo", "//evil.com/malicious");
    formData.append("next", "https://evil.com/malicious");

    const result = await loginAction({ success: false }, formData);

    expect(result).toBeUndefined();
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("prioritizes next parameter over redirectTo", async () => {
    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "validpassword");
    formData.append("redirectTo", "/fallback");
    formData.append("next", "/profile");

    const result = await loginAction({ success: false }, formData);

    expect(result).toBeUndefined();
    expect(mockRedirect).toHaveBeenCalledWith("/profile");
  });

  it("defaults to /dashboard when no redirect parameters provided", async () => {
    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "validpassword");

    const result = await loginAction({ success: false }, formData);

    expect(result).toBeUndefined();
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("returns fieldErrors for invalid email format", async () => {
    const formData = new FormData();
    formData.append("email", "not-an-email");
    formData.append("password", "password123");

    const result = await loginAction({ success: false }, formData);

    expect(result).toEqual({
      error: "Please check your input and try again",
      fieldErrors: {
        email: "Invalid email address",
      },
      success: false,
    });
    expect(SIGN_IN_MOCK).not.toHaveBeenCalled();
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("returns fieldErrors for missing password", async () => {
    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "");

    const result = await loginAction({ success: false }, formData);

    expect(result).toEqual({
      error: "Please check your input and try again",
      fieldErrors: {
        password: "Password is required",
      },
      success: false,
    });
    expect(SIGN_IN_MOCK).not.toHaveBeenCalled();
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("returns error for Supabase authentication failure", async () => {
    SIGN_IN_MOCK.mockResolvedValueOnce({
      error: new Error("Invalid login credentials"),
    });

    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "wrongpassword");

    const result = await loginAction({ success: false }, formData);

    expect(result).toEqual({
      error: "Invalid login credentials",
      success: false,
    });
    expect(SIGN_IN_MOCK).toHaveBeenCalled();
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("returns generic error message when Supabase error lacks message", async () => {
    SIGN_IN_MOCK.mockResolvedValueOnce({
      error: new Error(""),
    });

    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "password123");

    const result = await loginAction({ success: false }, formData);

    expect(result).toEqual({
      error: "Login failed",
      success: false,
    });
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("handles rememberMe checkbox (though it doesn't affect server-side auth)", async () => {
    const formData = new FormData();
    formData.append("email", "user@example.com");
    formData.append("password", "validpassword");
    formData.append("rememberMe", "on");

    const result = await loginAction({ success: false }, formData);

    expect(result).toBeUndefined();
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
    expect(SIGN_IN_MOCK).toHaveBeenCalledWith({
      email: "user@example.com",
      password: "validpassword",
    });
  });
});
