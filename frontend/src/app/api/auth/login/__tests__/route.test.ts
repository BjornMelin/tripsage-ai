/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const signInWithPassword = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { signInWithPassword },
  })),
}));

describe("POST /api/auth/login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    signInWithPassword.mockResolvedValue({ error: null });
  });

  it("authenticates valid credentials", async () => {
    const { POST } = await import("../route");
    const request = new Request("http://localhost/api/auth/login", {
      body: JSON.stringify({ email: "user@example.com", password: "password123" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const response = await POST(request);
    expect(response.status).toBe(200);
    expect(signInWithPassword).toHaveBeenCalledWith({
      email: "user@example.com",
      password: "password123",
    });
    expect(await response.json()).toEqual({ success: true });
  });

  it("returns validation errors for invalid payload", async () => {
    const { POST } = await import("../route");
    const request = new Request("http://localhost/api/auth/login", {
      body: JSON.stringify({ email: "not-an-email", password: "" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.success).toBe(false);
    expect(body.fieldErrors.email).toBeDefined();
    expect(body.fieldErrors.password).toBeDefined();
  });

  it("propagates Supabase auth failures", async () => {
    signInWithPassword.mockResolvedValueOnce({
      error: new Error("Invalid login credentials"),
    });
    const { POST } = await import("../route");
    const request = new Request("http://localhost/api/auth/login", {
      body: JSON.stringify({ email: "user@example.com", password: "wrong" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const response = await POST(request);
    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({
      error: "Invalid login credentials",
      success: false,
    });
  });

  it("handles unexpected errors gracefully", async () => {
    signInWithPassword.mockRejectedValueOnce(new Error("network down"));
    const { POST } = await import("../route");
    const request = new Request("http://localhost/api/auth/login", {
      body: JSON.stringify({ email: "user@example.com", password: "password123" }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const response = await POST(request);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error).toBe("An unexpected error occurred");
    expect(body.success).toBe(false);
  });
});
