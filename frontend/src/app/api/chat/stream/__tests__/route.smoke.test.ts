/**
 * @fileoverview Smoke tests for /api/chat/stream route, verifying basic functionality
 * and error handling with minimal mocking for fast execution and reliability.
 */

import type { NextRequest } from "next/server";
import type { LanguageModel } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  stubRateLimitDisabled,
  stubRateLimitEnabled,
  unstubAllEnvs,
} from "@/test/env-helpers";

/**
 * Builds a NextRequest object for testing API routes.
 *
 * @param body - Request body to be JSON stringified.
 * @param headers - Additional headers to include in the request.
 * @returns NextRequest object for testing.
 */
function buildReq(body: unknown, headers: Record<string, string> = {}): NextRequest {
  return new Request("http://localhost/api/chat/stream", {
    body: JSON.stringify(body),
    headers: { "content-type": "application/json", ...headers },
    method: "POST",
  }) as unknown as NextRequest;
}

describe("/api/chat/stream route smoke", () => {
  beforeEach(() => {
    vi.resetModules();
    unstubAllEnvs();
  });

  it("returns 401 unauthenticated (RL disabled)", async () => {
    stubRateLimitDisabled();
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: null } })) },
      })),
    }));
    const mod = await import("../route");
    const res = await mod.POST(buildReq({ messages: [] }));
    expect(res.status).toBe(401);
  });

  it("returns 429 when rate limited (auth ok)", async () => {
    stubRateLimitEnabled();
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      })),
    }));
    vi.doMock("@upstash/redis", () => ({ Redis: { fromEnv: vi.fn(() => ({})) } }));
    vi.doMock("@upstash/ratelimit", () => ({
      Ratelimit: class {
        static slidingWindow() {
          return {};
        }
        limit = vi.fn(async () => ({
          limit: 40,
          remaining: 0,
          reset: Date.now() + 60_000,
          success: false,
        }));
      },
    }));
    const mod = await import("../route");
    const res = await mod.POST(
      buildReq({ messages: [] }, { "x-forwarded-for": "1.2.3.4" })
    );
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
  });

  it("returns 200 on success with mocked provider and stream", async () => {
    stubRateLimitDisabled();
    // Authenticated user
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u2" } } })) },
      })),
    }));
    // Provider resolution mock
    vi.doMock("@/lib/providers/registry", () => ({
      resolveProvider: vi.fn(async () => ({
        model: {} as LanguageModel,
        modelId: "gpt-4o-mini",
        provider: "openai",
      })),
    }));
    // Stream stub
    vi.doMock("ai", () => ({
      convertToModelMessages: (x: unknown) => x,
      streamText: () => ({
        toUIMessageStreamResponse: () => new Response("ok", { status: 200 }),
      }),
    }));
    const mod = await import("../route");
    const res = await mod.POST(
      buildReq({
        messages: [{ id: "1", parts: [{ text: "hi", type: "text" }], role: "user" }],
      })
    );
    expect(res.status).toBe(200);
  });
});
