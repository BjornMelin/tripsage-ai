/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";

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
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("GET /api/keys route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns key metadata for authenticated user", async () => {
    const order = vi.fn().mockResolvedValue({
      data: [
        {
          created_at: "2025-11-01T00:00:00Z",
          last_used_at: null,
          service_name: "openai",
        },
      ],
      error: null,
    });
    const eq = vi.fn().mockReturnValue({ order });
    const select = vi.fn().mockReturnValue({ eq });
    const from = vi.fn().mockReturnValue({ select });
    MOCK_CREATE_SERVER_SUPABASE.mockResolvedValue({
      auth: { getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })) },
      from,
    } as unknown as TypedServerSupabase);
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
    MOCK_CREATE_SERVER_SUPABASE.mockResolvedValue({
      auth: { getUser: vi.fn(async () => ({ data: { user: null } })) },
    } as unknown as TypedServerSupabase);
    const { GET } = await import("../route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/keys",
    });
    const res = await GET(req, createRouteParamsContext());
    expect(res.status).toBe(401);
  });
});
