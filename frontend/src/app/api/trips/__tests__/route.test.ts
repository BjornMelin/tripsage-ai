/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { stubRateLimitDisabled } from "@/test/env-helpers";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";
import { setupUpstashMocks } from "@/test/setup/upstash";

const { redis, ratelimit } = setupUpstashMocks();

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

// Mock local Redis wrapper to return undefined (skip caching in tests)
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
}));

// Import after mocks are set up
import { GET as getTrips } from "../route";

describe("/api/trips route", () => {
  beforeEach(async () => {
    redis.__reset?.();
    ratelimit.__reset?.();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns 400 when filters are invalid", async () => {
    // Disable rate limiting for this test
    stubRateLimitDisabled();

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/trips?status=invalid&limit=not-a-number",
    });

    const res = await getTrips(req, createRouteParamsContext());

    expect(res.status).toBe(400);
  });
});
