/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/route-helpers";

const mockLogger = vi.hoisted(() => ({
  error: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
}));

const mockGetUserSecurityMetrics = vi.fn();

const adminSupabaseMock = {
  schema: vi.fn(() => ({
    from: vi.fn((table: string) => {
      if (table === "audit_log_entries") {
        return {
          select: vi.fn((_cols?: string, opts?: { head?: boolean; count?: string }) => {
            if (opts?.head) {
              return {
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn(async () => ({ count: 1, data: null, error: null })),
              };
            }
            return {
              eq: vi.fn().mockReturnThis(),
              limit: vi.fn(async () => ({
                data: [{ created_at: "2025-01-01T00:00:00Z" }],
                error: null,
              })),
              order: vi.fn().mockReturnThis(),
            };
          }),
        };
      }
      if (table === "sessions") {
        return {
          select: vi.fn(() => ({
            eq: vi.fn().mockReturnThis(),
            is: vi.fn(async () => ({ count: 2, data: null, error: null })),
          })),
        };
      }
      if (table === "mfa_factors") {
        return {
          select: vi.fn(() => ({
            eq: vi.fn(async () => ({ data: [{ id: "mfa-1" }], error: null })),
          })),
        };
      }
      return {
        select: vi.fn(() => ({
          eq: vi.fn().mockReturnThis(),
          neq: vi.fn(async () => ({ data: [{ provider: "github" }], error: null })),
        })),
      };
    }),
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

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => mockLogger),
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
  createAdminSupabase: vi.fn(() => adminSupabaseMock),
}));

vi.mock("@/lib/security/service", () => ({
  getUserSecurityMetrics: mockGetUserSecurityMetrics,
}));

describe("GET /api/security/metrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default successful response
    mockGetUserSecurityMetrics.mockResolvedValue({
      activeSessions: 2,
      failedLoginAttempts: 0,
      lastLogin: "2025-01-01T00:00:00Z",
      oauthConnections: ["github"],
      securityScore: 80,
      trustedDevices: 2,
    });
  });

  it("returns aggregated metrics", async () => {
    const { GET } = await import("../route");
    const res = await GET(
      createMockNextRequest({ method: "GET", url: "http://localhost" }),
      { ...createRouteParamsContext(), user: { id: "user-1" } as never } as never
    );
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      securityScore: number;
      activeSessions: number;
    };
    expect(body.activeSessions).toBeGreaterThanOrEqual(0);
    expect(body.securityScore).toBeGreaterThanOrEqual(0);
  });

  it("returns 400 with error response when validation fails", async () => {
    // Mock invalid metrics data that fails schema validation
    mockGetUserSecurityMetrics.mockResolvedValue({
      activeSessions: -1, // Invalid: negative number
      failedLoginAttempts: "invalid", // Invalid: not a number
      lastLogin: null, // Invalid: should be string
      oauthConnections: "not-an-array", // Invalid: should be array
      securityScore: 150, // Invalid: exceeds max
      trustedDevices: null, // Invalid: should be number
    });

    const { GET } = await import("../route");
    const res = await GET(
      createMockNextRequest({ method: "GET", url: "http://localhost" }),
      { ...createRouteParamsContext(), user: { id: "user-1" } as never } as never
    );

    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("invalid_metrics_shape");
    expect(body.reason).toBe("Metrics validation failed");
    expect(body.err).toBeUndefined();
    expect(mockLogger.error).toHaveBeenCalledWith(
      "Metrics validation failed",
      expect.objectContaining({
        error: expect.any(Object),
        issues: expect.any(Array),
        userId: "user-1",
      })
    );
  });

  it("returns 500 with error response when service throws", async () => {
    mockGetUserSecurityMetrics.mockRejectedValue(
      new Error("Database connection failed")
    );

    const { GET } = await import("../route");
    const res = await GET(
      createMockNextRequest({ method: "GET", url: "http://localhost" }),
      { ...createRouteParamsContext(), user: { id: "user-1" } as never } as never
    );

    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toBe("internal");
    expect(body.reason).toBe("Failed to fetch security metrics");
    expect(body.err).toBeUndefined();
    expect(mockLogger.error).toHaveBeenCalledWith(
      "Failed to fetch security metrics",
      expect.objectContaining({
        error: expect.any(Error),
        userId: "user-1",
      })
    );
  });
});
