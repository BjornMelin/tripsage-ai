/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const mockLogger = vi.hoisted(() => ({
  error: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
}));

const mockNowIso = vi.hoisted(() => vi.fn(() => "2025-01-01T03:00:00Z"));

const mockSpan = vi.hoisted(() => ({
  setAttribute: vi.fn(),
}));

const authUserResult = {
  data: { user: { id: "user-1" } },
  error: null,
};

const createAuthStub = (overrides?: Partial<Record<string, unknown>>) => ({
  getUser: vi.fn(async () => authUserResult),
  ...overrides,
});

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => mockLogger),
}));

vi.mock("@/lib/security/random", () => ({
  nowIso: mockNowIso,
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _opts: unknown, execute: unknown) =>
    (execute as (span: unknown) => unknown)(mockSpan)
  ),
}));

describe("lib/security/sessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists sessions and marks the current session", async () => {
    const mockSessionRow = {
      created_at: "2025-01-01T00:00:00Z",
      id: "sess-1",
      ip: "192.0.2.1",
      not_after: null,
      refreshed_at: "2025-01-01T01:00:00Z",
      updated_at: "2025-01-01T01:00:00Z",
      user_agent: "Chrome on macOS",
      user_id: "user-1",
    };

    const mockSessionRow2 = {
      created_at: "2025-01-01T00:00:00Z",
      id: "sess-2",
      ip: { address: "203.0.113.9" },
      not_after: null,
      refreshed_at: null,
      updated_at: "2025-01-01T02:00:00Z",
      user_agent: null,
      user_id: "user-1",
    };

    const query = {
      eq: vi.fn().mockReturnThis(),
      is: vi.fn().mockReturnThis(),
      limit: vi.fn(async () => ({
        data: [mockSessionRow, mockSessionRow2],
        error: null,
      })),
      order: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
    };

    const adminSupabase = {
      schema: vi.fn(() => ({ from: vi.fn(() => query) })),
    };

    const { listActiveSessions } = await import("@/lib/security/sessions");
    const sessions = await listActiveSessions(adminSupabase as never, "user-1", {
      currentSessionId: "sess-1",
    });

    expect(sessions).toHaveLength(2);
    expect(sessions[0]).toMatchObject({
      browser: "Chrome on macOS",
      device: "Chrome on macOS",
      id: "sess-1",
      ipAddress: "192.0.2.1",
      isCurrent: true,
      lastActivity: "2025-01-01T01:00:00Z",
      location: "Unknown",
    });
    expect(sessions[1]).toMatchObject({
      browser: "Unknown",
      device: "Unknown device",
      id: "sess-2",
      ipAddress: "203.0.113.9",
      isCurrent: false,
      lastActivity: "2025-01-01T02:00:00Z",
      location: "Unknown",
    });
  });

  it("parses current session id from access token payload", async () => {
    const tokenFor = (payload: Record<string, unknown>) =>
      `h.${Buffer.from(JSON.stringify(payload)).toString("base64url")}.s`;

    const supabase = {
      auth: createAuthStub({
        getSession: vi.fn(async () => ({
          data: { session: { access_token: tokenFor({ session_id: "sess-1" }) } },
          error: null,
        })),
      }),
    };

    const { getCurrentSessionId } = await import("@/lib/security/sessions");
    await expect(getCurrentSessionId(supabase as never)).resolves.toBe("sess-1");
  });

  it("falls back to sessionId claim when present", async () => {
    const token = `h.${Buffer.from(JSON.stringify({ sessionId: "sess-2" })).toString(
      "base64url"
    )}.s`;
    const supabase = {
      auth: createAuthStub({
        getSession: vi.fn(async () => ({
          data: { session: { access_token: token } },
          error: null,
        })),
      }),
    };

    const { getCurrentSessionId } = await import("@/lib/security/sessions");
    await expect(getCurrentSessionId(supabase as never)).resolves.toBe("sess-2");
  });

  it("returns null for invalid or missing access tokens", async () => {
    const supabase = {
      auth: createAuthStub({
        getSession: vi.fn(async () => ({
          data: { session: { access_token: "not-a-jwt" } },
          error: null,
        })),
      }),
    };

    const { getCurrentSessionId } = await import("@/lib/security/sessions");
    await expect(getCurrentSessionId(supabase as never)).resolves.toBeNull();
  });

  it("returns null and warns on invalid token payload", async () => {
    const supabase = {
      auth: createAuthStub({
        getSession: vi.fn(async () => ({
          data: { session: { access_token: "h.!@#.s" } },
          error: null,
        })),
      }),
    };

    const { getCurrentSessionId } = await import("@/lib/security/sessions");
    await expect(getCurrentSessionId(supabase as never)).resolves.toBeNull();
    expect(mockLogger.warn).toHaveBeenCalledWith(
      "session_id_parse_failed",
      expect.any(Object)
    );
  });

  it("returns null and warns when getSession returns an error", async () => {
    const supabase = {
      auth: createAuthStub({
        getSession: vi.fn(async () => ({
          data: { session: null },
          error: { message: "bad_session" },
        })),
      }),
    };

    const { getCurrentSessionId } = await import("@/lib/security/sessions");
    await expect(getCurrentSessionId(supabase as never)).resolves.toBeNull();
    expect(mockLogger.warn).toHaveBeenCalledWith("session_fetch_failed", {
      error: "bad_session",
    });
  });

  it("returns null and logs when getSession throws", async () => {
    const supabase = {
      auth: createAuthStub({
        getSession: vi.fn(() => {
          throw new Error("boom");
        }),
      }),
    };

    const { getCurrentSessionId } = await import("@/lib/security/sessions");
    await expect(getCurrentSessionId(supabase as never)).resolves.toBeNull();
    expect(mockLogger.error).toHaveBeenCalledWith("session_fetch_exception", {
      error: "boom",
    });
  });

  it("throws SessionsListError on database query failures", async () => {
    const query = {
      eq: vi.fn().mockReturnThis(),
      is: vi.fn().mockReturnThis(),
      limit: vi.fn(async () => ({ data: null, error: { message: "db_down" } })),
      order: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
    };

    const adminSupabase = {
      schema: vi.fn(() => ({ from: vi.fn(() => query) })),
    };

    const { SessionsListError, listActiveSessions } = await import(
      "@/lib/security/sessions"
    );

    await expect(
      listActiveSessions(adminSupabase as never, "user-1")
    ).rejects.toBeInstanceOf(SessionsListError);
  });

  it("throws SessionsListError on invalid mapped shape", async () => {
    const badRow = {
      created_at: "2025-01-01T00:00:00Z",
      // id missing -> invalid
      ip: "192.0.2.1",
      not_after: null,
      refreshed_at: "2025-01-01T01:00:00Z",
      updated_at: "2025-01-01T01:00:00Z",
      user_agent: "Chrome on macOS",
      user_id: "user-1",
    };

    const query = {
      eq: vi.fn().mockReturnThis(),
      is: vi.fn().mockReturnThis(),
      limit: vi.fn(async () => ({ data: [badRow], error: null })),
      order: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
    };

    const adminSupabase = {
      schema: vi.fn(() => ({ from: vi.fn(() => query) })),
    };

    const { SessionsListError, listActiveSessions } = await import(
      "@/lib/security/sessions"
    );

    await expect(
      listActiveSessions(adminSupabase as never, "user-1")
    ).rejects.toBeInstanceOf(SessionsListError);
    expect(mockLogger.error).toHaveBeenCalledWith(
      "sessions_list_invalid_shape",
      expect.any(Object)
    );
  });

  it("maps sessions with Unknown lastActivity when missing timestamps", async () => {
    const row = {
      created_at: null,
      id: "sess-unknown",
      ip: "192.0.2.1",
      refreshed_at: null,
      updated_at: null,
      user_agent: null,
    };

    const { mapSessionRow } = await import("@/lib/security/sessions");
    const session = mapSessionRow(row as never, "sess-current");

    expect(session).toMatchObject({
      browser: "Unknown",
      device: "Unknown device",
      id: "sess-unknown",
      ipAddress: "192.0.2.1",
      isCurrent: false,
      lastActivity: "Unknown",
      location: "Unknown",
    });
    expect(mockLogger.warn).toHaveBeenCalledWith("session_missing_activity_timestamp", {
      observedAt: "2025-01-01T03:00:00Z",
    });
    expect(mockNowIso).toHaveBeenCalled();
  });
});
