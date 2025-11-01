/**
 * @fileoverview Unit tests for BYOK key validation route handler.
 */
import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/keys/validate route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("returns is_valid true on provider 200", async () => {
    (globalThis.fetch as unknown as any).mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 })
    );
    vi.mock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      })),
    }));
    const { POST } = await import("../route");
    const req = {
      json: async () => ({ service: "openai", api_key: "sk-test" }),
      headers: new Headers(),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ is_valid: true });
  });

  it("returns is_valid false on 401/403", async () => {
    (globalThis.fetch as unknown as any).mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 401 })
    );
    vi.mock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      })),
    }));
    const { POST } = await import("../route");
    const req = {
      json: async () => ({ service: "openai", api_key: "bad" }),
      headers: new Headers(),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.is_valid).toBe(false);
  });
});
