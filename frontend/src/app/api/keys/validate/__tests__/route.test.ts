/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { stubRateLimitDisabled, unstubAllEnvs } from "@/test/env-helpers";

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
      limit: 10,
      remaining: 9,
      reset: Date.now() + 60000,
      success: true,
    }),
  };

  return {
    Ratelimit: vi.fn().mockImplementation(() => mockInstance),
    slidingWindow: vi.fn(),
  };
});

// Mock Supabase server client to avoid env/cookie requirements
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: "u1" } },
        error: null,
      }),
    },
  })),
}));

describe("/api/keys/validate route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    unstubAllEnvs();
    stubRateLimitDisabled();
    // Ensure Supabase SSR client does not throw when real module is imported
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon-test-key");
  });

  describe("successful validation", () => {
    it("returns is_valid true on provider 200", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))
      );

      // Import after setting up mocks (do not reset after mocking)
      const { POST } = await import("../route");
      const req = {
        headers: new Headers(),
        json: async () => ({ apiKey: "sk-test", service: "openai" }),
      } as unknown as NextRequest;

      try {
        const res = await POST(req);
        const body = await res.json();
        // Assert both status and body together to surface diff when failing
        expect({ body, status: res.status }).toEqual({
          body: { isValid: true },
          status: 200,
        });
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
