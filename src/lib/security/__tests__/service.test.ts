/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { withFakeTimers } from "@/test/utils/with-fake-timers";

const getManyMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabase/typed-helpers", () => ({
  getMany: getManyMock,
}));

import { getUserSecurityMetrics, getUserSessions } from "../service";

type QueryCall = {
  column: string;
  method: string;
  value: unknown;
};

type QueryRecorder = {
  eq: (column: string, value: unknown) => QueryRecorder;
  gte: (column: string, value: unknown) => QueryRecorder;
};

function createQueryRecorder(): { calls: QueryCall[]; query: QueryRecorder } {
  const calls: QueryCall[] = [];
  const query: QueryRecorder = {
    eq: (column, value) => {
      calls.push({ column, method: "eq", value });
      return query;
    },
    gte: (column, value) => {
      calls.push({ column, method: "gte", value });
      return query;
    },
  };
  return { calls, query };
}

describe("security service session mapping", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("prefers refreshed, updated, and created timestamps in order", async () => {
    getManyMock.mockResolvedValue({
      data: [
        {
          created_at: "2026-01-01T00:00:00.000Z",
          id: "session-1",
          ip: "192.0.2.1",
          refreshed_at: "2026-01-01T03:00:00.000Z",
          updated_at: "2026-01-01T02:00:00.000Z",
          user_agent: "Chrome",
        },
        {
          created_at: "2026-01-02T00:00:00.000Z",
          id: "session-2",
          ip: null,
          refreshed_at: null,
          updated_at: "2026-01-02T02:00:00.000Z",
          user_agent: null,
        },
        {
          created_at: "2026-01-03T00:00:00.000Z",
          id: "session-3",
          ip: "203.0.113.1",
          refreshed_at: null,
          updated_at: null,
          user_agent: "Firefox",
        },
      ],
      error: null,
    });

    const sessions = await getUserSessions({} as never, "user-1");

    expect(sessions.map((session) => session.lastActivity)).toEqual([
      "2026-01-01T03:00:00.000Z",
      "2026-01-02T02:00:00.000Z",
      "2026-01-03T00:00:00.000Z",
    ]);
  });

  it("uses Unknown instead of fabricating fresh activity for missing timestamps", async () => {
    getManyMock.mockResolvedValue({
      data: [
        {
          created_at: null,
          id: "session-missing",
          ip: null,
          refreshed_at: null,
          updated_at: null,
          user_agent: null,
        },
      ],
      error: null,
    });

    const sessions = await getUserSessions({} as never, "user-1");

    expect(sessions).toHaveLength(1);
    expect(sessions[0]).toMatchObject({
      browser: "Unknown",
      device: "Unknown device",
      id: "session-missing",
      ipAddress: "Unknown",
      isCurrent: false,
      lastActivity: "Unknown",
      location: "Unknown",
    });
  });
});

describe("security service metrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it(
    "derives failed-login cutoff from the shared timestamp helper",
    withFakeTimers(async () => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));
      getManyMock
        .mockResolvedValueOnce({
          data: [{ created_at: "2026-02-03T03:00:00.000Z" }],
          error: null,
        })
        .mockResolvedValueOnce({ count: 2, data: [], error: null })
        .mockResolvedValueOnce({ count: 1, data: [], error: null })
        .mockResolvedValueOnce({ data: [{ id: "mfa-1" }], error: null })
        .mockResolvedValueOnce({
          data: [{ provider: "google" }],
          error: null,
        });

      const metrics = await getUserSecurityMetrics({} as never, "user-1");

      expect(metrics).toEqual({
        activeSessions: 1,
        failedLoginAttempts: 2,
        lastLogin: "2026-02-03T03:00:00.000Z",
        oauthConnections: ["google"],
        securityScore: 90,
        trustedDevices: 1,
      });

      const failedLoginFilter = getManyMock.mock.calls[1]?.[2] as
        | ((query: QueryRecorder) => QueryRecorder)
        | undefined;
      expect(failedLoginFilter).toBeTypeOf("function");
      if (!failedLoginFilter) {
        throw new Error("missing_failed_login_filter");
      }

      const { calls, query } = createQueryRecorder();
      failedLoginFilter(query);

      expect(calls).toContainEqual({
        column: "created_at",
        method: "gte",
        value: "2026-02-02T04:05:06.000Z",
      });
    })
  );
});
