/**
 * @fileoverview Smoke tests for /api/chat route, verifying basic auth handling
 * and happy-path wiring with minimal mocking.
 */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unstubAllEnvs } from "@/test/env-helpers";

/**
 * Builds a NextRequest object for testing API routes.
 *
 * @param body - Request body to be JSON stringified.
 * @param headers - Additional headers to include in the request.
 * @returns NextRequest object for testing.
 */
function buildReq(body: unknown, headers: Record<string, string> = {}): NextRequest {
  return new Request("http://localhost/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  }) as unknown as NextRequest;
}

describe("/api/chat route smoke", () => {
  beforeEach(() => {
    vi.resetModules();
    unstubAllEnvs();
  });

  it("returns 401 unauthenticated", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: null } })) },
      })),
    }));
    const mod = await import("../route");
    const res = await mod.POST(buildReq({ messages: [] }));
    expect(res.status).toBe(401);
  });

  it("returns 200 on success", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
        from: vi.fn(() => ({ insert: vi.fn(async () => ({ error: null })) })),
      })),
    }));
    vi.doMock("@/lib/providers/registry", () => ({
      resolveProvider: vi.fn(async () => ({
        provider: "openai",
        modelId: "gpt-4o-mini",
        model: {},
      })),
    }));
    vi.doMock("ai", () => ({
      convertToModelMessages: (x: unknown) => x,
      generateText: vi.fn(async () => ({
        text: "ok",
        usage: { totalTokens: 3, inputTokens: 1, outputTokens: 2 },
      })),
    }));
    const mod = (await import("../route")) as any;
    const res = await mod.POST(buildReq({ messages: [] }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.content).toBe("ok");
    expect(body.model).toBe("gpt-4o-mini");
  });
});
