/**
 * @fileoverview Unit tests for BYOK key validation route handler.
 */
import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock external dependencies at the top level
vi.mock("@/lib/next/route-helpers", () => ({
  buildRateLimitKey: vi.fn(() => "test-key"),
}));

vi.mock("@upstash/redis", () => ({
  Redis: {
    fromEnv: vi.fn(() => ({})),
  },
}));

vi.mock("@upstash/ratelimit", () => {
  const mockInstance = {
    limit: vi.fn().mockResolvedValue({
      success: true,
      limit: 10,
      remaining: 9,
      reset: Date.now() + 60000,
    }),
  };

  return {
    Ratelimit: vi.fn().mockImplementation(() => mockInstance),
    slidingWindow: vi.fn(),
  };
});

describe("/api/keys/validate route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.unstubAllGlobals();

    // Set environment variables for testing
    process.env.UPSTASH_REDIS_REST_URL = "mock-url";
    process.env.UPSTASH_REDIS_REST_TOKEN = "mock-token";
  });

  describe("successful validation", () => {
    it("returns is_valid true on provider 200", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))
      );

      vi.doMock("@/lib/supabase/server", () => ({
        createServerSupabase: vi.fn().mockResolvedValue({
          auth: {
            getUser: vi.fn().mockResolvedValue({
              data: { user: { id: "u1" } },
              error: null,
            }),
          },
        }),
      }));

      const { POST } = await import("../route");
      const req = {
        json: async () => ({ service: "openai", api_key: "sk-test" }),
        headers: new Headers(),
      } as unknown as NextRequest;

      try {
        const res = await POST(req);

        // Debug: log the response if it's an error
        if (res.status === 500) {
          const body = await res.json();
          console.error("Test failed with 500 error:", body);
        }

        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body).toEqual({ is_valid: true });
      } catch (error) {
        console.error("Test threw an error:", error);
        if (error instanceof Error && error.stack) {
          console.error("Error stack:", error.stack);
        }
        throw error;
      }
    });
  });
});
