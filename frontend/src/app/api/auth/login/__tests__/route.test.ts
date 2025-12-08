/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRouteParamsContext,
  getApiRouteSupabaseMock,
  makeJsonRequest,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

describe("POST /api/auth/login", () => {
  beforeEach(() => {
    resetApiRouteMocks();
  });

  it("authenticates valid credentials", async () => {
    const supabase = getApiRouteSupabaseMock();
    const signInWithPassword = vi.fn().mockResolvedValue({ error: null });
    supabase.auth.signInWithPassword = signInWithPassword;

    const { POST } = await import("../route");
    const request = makeJsonRequest("http://localhost/api/auth/login", {
      email: "user@example.com",
      password: "password123",
    });

    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(200);
    expect(signInWithPassword).toHaveBeenCalledWith({
      email: "user@example.com",
      password: "password123",
    });
    expect(await response.json()).toEqual({ success: true });
  });

  it("returns validation errors for invalid payload", async () => {
    const supabase = getApiRouteSupabaseMock();
    const signInWithPassword = supabase.auth.signInWithPassword;

    const { POST } = await import("../route");
    const request = makeJsonRequest("http://localhost/api/auth/login", {
      email: "not-an-email",
      password: "",
    });

    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(400);
    const body = await response.json();
    // withApiGuards returns standardized validation error format
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toBe("Request validation failed");
    expect(body.issues).toBeDefined();
    expect(Array.isArray(body.issues)).toBe(true);
    expect(signInWithPassword).not.toHaveBeenCalled();
  });

  it("propagates Supabase auth failures", async () => {
    const supabase = getApiRouteSupabaseMock();
    const signInWithPassword = vi
      .fn()
      .mockResolvedValue({ error: new Error("Invalid login credentials") });
    supabase.auth.signInWithPassword = signInWithPassword;

    const { POST } = await import("../route");
    const request = makeJsonRequest("http://localhost/api/auth/login", {
      email: "user@example.com",
      password: "wrong",
    });

    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body.error).toBe("invalid_credentials");
    expect(body.reason).toBe("Invalid email or password");
  });

  it("returns 403 when MFA is required", async () => {
    const supabase = getApiRouteSupabaseMock();
    const signInWithPassword = vi.fn().mockResolvedValue({
      data: { session: null, user: null },
      error: {
        code: "insufficient_aal",
        message: "MFA required",
        status: 403,
      },
    });
    supabase.auth.signInWithPassword = signInWithPassword;

    const { POST } = await import("../route");
    const request = makeJsonRequest("http://localhost/api/auth/login", {
      email: "user@example.com",
      password: "password123",
    });

    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(403);
    const body = await response.json();
    expect(body.error).toBe("mfa_required");
    expect(body.reason).toBe("Multi-factor authentication required");
    expect(body.code).toBe("insufficient_aal");
  });

  it("handles unexpected errors gracefully", async () => {
    const supabase = getApiRouteSupabaseMock();
    const signInWithPassword = vi.fn().mockRejectedValue(new Error("network down"));
    supabase.auth.signInWithPassword = signInWithPassword;

    const { POST } = await import("../route");
    const request = makeJsonRequest("http://localhost/api/auth/login", {
      email: "user@example.com",
      password: "password123",
    });

    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(500);
    const body = await response.json();
    // withApiGuards catches and returns standardized internal error
    expect(body.error).toBe("internal");
    expect(body.reason).toBe("Internal server error");
  });
});
