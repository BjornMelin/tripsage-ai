/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

const mockLogger = vi.hoisted(() => ({
  error: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
}));

const mockSpan = vi.hoisted(() => ({
  setAttribute: vi.fn(),
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => mockLogger),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _opts: unknown, execute: unknown) =>
    (execute as (span: unknown) => unknown)(mockSpan)
  ),
}));

describe("lib/security/sessions", () => {
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
});
