/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";

const auditRows = [
  {
    created_at: "2025-01-01T00:00:00Z",
    id: "evt-1",
    ip_address: "192.0.2.10",
    payload: { action: "login", user_agent: "Chrome", user_id: "user-1" },
  },
];

const adminMock = {
  schema: vi.fn(() => ({
    from: vi.fn(() => ({
      eq: vi.fn().mockReturnThis(),
      limit: vi.fn(async () => ({ data: auditRows, error: null })),
      order: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
    })),
  })),
};

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "token" }))
  ),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => ({})),
}));

vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});
vi.mock("@/lib/api/factory", () => ({
  withApiGuards: () => (handler: unknown) => handler,
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getSession: vi.fn(async () => ({
        data: { session: { access_token: "token" } },
        error: null,
      })),
      getUser: vi.fn(async () => ({ data: { user: { id: "user-1" } }, error: null })),
    },
  })),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: vi.fn(() => adminMock),
}));
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getSession: vi.fn(async () => ({
        data: { session: { access_token: "token" } },
        error: null,
      })),
      getUser: vi.fn(async () => ({ data: { user: { id: "user-1" } }, error: null })),
    },
  })),
}));

describe("GET /api/security/events", () => {
  it("returns mapped security events", async () => {
    const { GET } = await import("../route");
    const res = await GET(
      createMockNextRequest({ method: "GET", url: "http://localhost" }),
      { ...createRouteParamsContext(), user: { id: "user-1" } as never } as never
    );

    expect(res.status).toBe(200);
    const body = (await res.json()) as Array<{
      id: string;
      type: string;
      riskLevel: string;
    }>;
    expect(body[0]).toMatchObject({
      id: "evt-1",
      riskLevel: "low",
      type: "login_success",
    });
  });
});
