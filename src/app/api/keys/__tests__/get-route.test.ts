/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setRateLimitFactoryForTests } from "@/lib/api/factory";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";
import { createMockSupabaseClient, getSupabaseMockState } from "@/test/mocks/supabase";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const MOCK_CREATE_SERVER_SUPABASE = vi.hoisted(() => vi.fn());
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: MOCK_CREATE_SERVER_SUPABASE,
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
}));

// Mock route helpers
vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("GET /api/keys route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setRateLimitFactoryForTests(async () => ({
      limit: 60,
      remaining: 59,
      reset: Date.now() + 60_000,
      success: true,
    }));
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
  });

  it("returns key metadata for authenticated user", async () => {
    const supabase = createMockSupabaseClient({ user: { id: "u1" } });
    getSupabaseMockState(supabase).selectResult = {
      count: null,
      data: [
        {
          created_at: "2025-11-01T00:00:00Z",
          last_used: null,
          service: "openai",
          user_id: "u1",
        },
      ],
      error: null,
    };
    MOCK_CREATE_SERVER_SUPABASE.mockResolvedValue(supabase);
    const { GET } = await import("../route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/keys",
    });
    const res = await GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body[0]).toMatchObject({ hasKey: true, isValid: true, service: "openai" });
  });

  it("returns 401 when not authenticated", async () => {
    MOCK_CREATE_SERVER_SUPABASE.mockResolvedValue(
      createMockSupabaseClient({ user: null })
    );
    const { GET } = await import("../route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/keys",
    });
    const res = await GET(req, createRouteParamsContext());
    expect(res.status).toBe(401);
  });
});
