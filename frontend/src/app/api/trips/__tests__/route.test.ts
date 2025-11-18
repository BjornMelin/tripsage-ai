/** @vitest-environment node */

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getMockCookiesForTest, createMockNextRequest } from "@/test/route-helpers";
import { stubRateLimitDisabled } from "@/test/env-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() => Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))),
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
    from: vi.fn().mockReturnValue({
      eq: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      ilike: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
    }),
  })),
}));

// Mock Redis for rate limiting
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

// Import after mocks are set up
import { GET as getTrips } from "../route";

afterEach(() => {
  vi.clearAllMocks();
});

describe("/api/trips route", () => {
  it("returns 400 when filters are invalid", async () => {
    // Disable rate limiting for this test
    stubRateLimitDisabled();

    const req = createMockNextRequest({
      url: "http://localhost/api/trips?status=invalid&limit=not-a-number",
      method: "GET",
    });

    const res = await getTrips(req);

    expect(res.status).toBe(400);
  });
});
