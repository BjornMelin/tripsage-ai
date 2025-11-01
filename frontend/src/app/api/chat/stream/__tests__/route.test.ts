/**
 * @fileoverview Focused tests for /api/chat/stream route hardening.
 */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "../route";

// Helper to build a NextRequest-like object for testing
function buildReq(body: unknown, headers: Record<string, string> = {}): NextRequest {
  const req = new Request("http://localhost/api/chat/stream", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  }) as unknown as NextRequest;
  return req;
}

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => {
  return {
    createServerSupabase: vi.fn(async () => ({
      auth: {
        getUser: vi.fn(async () => ({ data: { user: null } })),
      },
      from: vi.fn(() => ({
        select: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        order: vi.fn().mockReturnThis(),
        limit: vi.fn().mockReturnThis(),
        insert: vi.fn(async () => ({ error: null })),
        update: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn(async () => ({ data: null, error: null })),
      })),
    })),
  };
});

// Mock provider registry to avoid network
vi.mock("@/lib/providers/registry", () => {
  return {
    resolveProvider: vi.fn(async () => ({
      provider: "openai",
      modelId: "gpt-4o-mini",
      model: {} as any,
    })),
  };
});

describe("/api/chat/stream", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns 401 unauthenticated", async () => {
    const req = buildReq({ messages: [] });
    const res = await POST(req);
    expect(res.status).toBe(401);
    const data = (await res.json()) as any;
    expect(data.error).toBe("unauthorized");
  });

  it("returns 429 when rate limited and sets Retry-After", async () => {
    // Re-mock Supabase to have a user
    const { createServerSupabase } = await import("@/lib/supabase/server");
    (createServerSupabase as any).mockResolvedValueOnce({
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      from: vi.fn(),
    });

    // Mock Upstash limiter to fail
    vi.doMock("@upstash/ratelimit", () => ({
      Ratelimit: class {
        limit = vi.fn(async () => ({ success: false }));
      },
    }));

    const req = buildReq({ messages: [] }, { "x-forwarded-for": "1.2.3.4" });
    const res = await POST(req);
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
  });

  it("rejects non-image attachments", async () => {
    const { createServerSupabase } = await import("@/lib/supabase/server");
    (createServerSupabase as any).mockResolvedValueOnce({
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u2" } } })) },
      from: vi.fn(),
    });

    const req = buildReq({
      messages: [
        {
          id: "m1",
          role: "user",
          parts: [
            { type: "text", text: "hello" },
            { type: "file", url: "https://x/y.pdf", media_type: "application/pdf" },
          ],
        },
      ],
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const data = (await res.json()) as any;
    expect(data.error).toBe("invalid_attachment");
  });

  it("clamps tokens and returns 400 when no output tokens available", async () => {
    const { createServerSupabase } = await import("@/lib/supabase/server");
    (createServerSupabase as any).mockResolvedValueOnce({
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u3" } } })) },
      from: vi.fn(() => ({
        select: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        order: vi.fn().mockReturnThis(),
        limit: vi.fn().mockReturnThis(),
      })),
    });

    const huge = "x".repeat(128_000 * 4 + 10_000); // heuristic token count overflow
    const req = buildReq({
      messages: [{ id: "u", role: "user", parts: [{ type: "text", text: huge }] }],
      desiredMaxTokens: 5000,
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const data = (await res.json()) as any;
    expect(String(data.error)).toMatch(/No output tokens available/i);
  });
});
