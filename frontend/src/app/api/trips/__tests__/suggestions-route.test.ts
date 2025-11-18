/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { stubRateLimitDisabled } from "@/test/env-helpers";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
        error: null,
      }),
    },
  })),
}));

// Mock Redis for rate limiting
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

// Mock AI provider registry
vi.mock("@/lib/providers/registry", () => ({
  resolveProvider: vi.fn(async () => ({ model: "test-model" })),
}));

// Mock AI SDK
vi.mock("ai", () => ({
  generateObject: vi.fn(async () => ({ object: { suggestions: [] } })),
}));

// Import after mocks are set up
import { GET as getSuggestions } from "../suggestions/route";

describe("/api/trips/suggestions route", () => {
  it("returns 401 when user is missing", async () => {
    // Disable rate limiting for this test
    stubRateLimitDisabled();

    // Mock unauthenticated user
    const { createServerSupabase } = await import("@/lib/supabase/server");
    vi.mocked(createServerSupabase).mockResolvedValueOnce({
      auth: {
        getUser: async () => ({
          data: { user: null },
          error: new Error("Unauthorized"),
        }),
      },
    } as any);

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/suggestions",
    });

    const res = await getSuggestions(req);

    expect(res.status).toBe(401);
  });

  it("returns suggestions array when generation succeeds", async () => {
    // Disable rate limiting for this test
    stubRateLimitDisabled();

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips/suggestions?limit=3",
    });

    const res = await getSuggestions(req);

    expect(res.status).toBe(200);
    const body = (await res.json()) as unknown[];
    expect(Array.isArray(body)).toBe(true);
  });
});
