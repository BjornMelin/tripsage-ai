/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";
import { DELETE } from "../[sessionId]/route";
import { GET } from "../route";

const accessTokenWithSession = (sessionId: string) => {
  const payload = { session_id: sessionId };
  const base64 = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `header.${base64}.sig`;
};

const mockSessionRow = {
  aal: null,
  created_at: "2025-01-01T00:00:00Z",
  factor_id: null,
  id: "sess-1",
  ip: "192.0.2.1",
  not_after: null,
  oauth_client_id: null,
  refreshed_at: "2025-01-01T01:00:00Z",
  tag: null,
  updated_at: "2025-01-01T01:00:00Z",
  user_agent: "Chrome on macOS",
  user_id: "user-1",
};

const supabaseMock = {
  auth: {
    getSession: vi.fn(),
    getUser: vi.fn(),
  },
};

const adminMock = () => {
  const query = {
    delete: vi.fn(() => ({
      eq: vi.fn(() => ({
        eq: vi.fn(async () => ({ error: null })),
      })),
    })),
    eq: vi.fn().mockReturnThis(),
    is: vi.fn().mockReturnThis(),
    limit: vi.fn(async () => ({ data: [mockSessionRow], error: null })),
    maybeSingle: vi.fn(async () => ({ data: mockSessionRow, error: null })),
    order: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
  };

  return {
    schema: vi.fn(() => ({ from: vi.fn(() => query) })),
  };
};

let adminInstance: ReturnType<typeof adminMock> = adminMock();

describe("/api/security/sessions routes", () => {
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

  vi.mock("@/lib/supabase/server", () => ({
    createServerSupabase: vi.fn(async () => supabaseMock),
  }));

  vi.mock("@/lib/supabase/admin", () => ({
    createAdminSupabase: vi.fn(() => adminInstance),
  }));

  beforeEach(() => {
    vi.clearAllMocks();
    supabaseMock.auth.getSession.mockReset();
    supabaseMock.auth.getUser.mockReset();
    adminInstance = adminMock();
  });

  it("lists sessions and marks current session", async () => {
    supabaseMock.auth.getSession.mockResolvedValue({
      data: { session: { access_token: accessTokenWithSession("sess-1") } },
      error: null,
    });
    supabaseMock.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-1" } },
      error: null,
    });
    adminInstance = adminMock();

    const res = await GET(
      createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/security/sessions",
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(200);
    const body = (await res.json()) as Array<{ id: string; isCurrent: boolean }>;
    expect(body).toHaveLength(1);
    expect(body[0]?.id).toBe("sess-1");
    expect(body[0]?.isCurrent).toBe(true);
  });

  it("terminates a session for the authenticated user", async () => {
    supabaseMock.auth.getSession.mockResolvedValue({
      data: { session: null },
      error: null,
    });
    supabaseMock.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-1" } },
      error: null,
    });

    const deleteChain = {
      eq: vi.fn(() => ({
        eq: vi.fn(async () => ({ error: null })),
      })),
    };

    adminInstance = {
      schema: vi.fn(() => ({
        from: vi.fn(() => ({
          delete: vi.fn(() => deleteChain),
          eq: vi.fn().mockReturnThis(),
          maybeSingle: vi.fn(async () => ({ data: mockSessionRow, error: null })),
          select: vi.fn().mockReturnThis(),
        })),
      })),
    } as unknown as ReturnType<typeof adminMock>;

    const res = await DELETE(
      createMockNextRequest({
        method: "DELETE",
        url: "http://localhost/api/security/sessions/sess-1",
      }),
      { params: Promise.resolve({ sessionId: "sess-1" }) }
    );

    expect(res.status).toBe(204);
  });
});
