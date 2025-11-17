/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() before any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const MOCK_SUPABASE = vi.hoisted(() => ({
  auth: {
    getUser: vi.fn(),
  },
  from: vi.fn(),
}));

const CREATE_SUPABASE = vi.hoisted(() => vi.fn(async () => MOCK_SUPABASE));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE,
}));

vi.mock("@/lib/supabase/rpc", () => ({
  getUserAllowGatewayFallback: vi.fn(async () => true),
}));

function mockTableUpsert(ok = true) {
  const upsert = vi.fn(async () => ({ error: ok ? null : new Error("db") }));
  const builder = { upsert } as unknown as { upsert: typeof upsert };
  MOCK_SUPABASE.from.mockReturnValue(builder);
  return { upsert };
}

describe("/api/user-settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    CREATE_SUPABASE.mockResolvedValue(MOCK_SUPABASE);
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "u1" } },
      error: null,
    });
  });

  it("GET returns allowGatewayFallback for authenticated user", async () => {
    const { GET } = await import("../route");
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ allowGatewayFallback: true });
  });

  it("GET returns 401 when user is missing", async () => {
    MOCK_SUPABASE.auth.getUser.mockResolvedValueOnce({
      data: { user: null },
      error: null,
    });
    const { GET } = await import("../route");
    const res = await GET();
    expect(res.status).toBe(401);
  });

  it("POST upserts consent flag", async () => {
    const { upsert } = mockTableUpsert(true);
    const { POST } = await import("../route");
    const req = createMockNextRequest({
      body: { allowGatewayFallback: false },
      method: "POST",
      url: "http://localhost/api/user-settings",
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(upsert).toHaveBeenCalledWith(
      { allow_gateway_fallback: false, user_id: "u1" },
      { ignoreDuplicates: false, onConflict: "user_id" }
    );
  });

  it("POST rejects malformed JSON", async () => {
    const { POST } = await import("../route");
    const req = createMockNextRequest({
      body: {},
      method: "POST",
      url: "http://localhost/api/user-settings",
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});
