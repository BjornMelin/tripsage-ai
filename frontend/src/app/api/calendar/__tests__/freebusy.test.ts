import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const mockQueryFreeBusy = vi.fn();
vi.mock("@/lib/calendar/google", () => ({
  queryFreeBusy: mockQueryFreeBusy,
}));

const mockLimitFn = vi.fn().mockResolvedValue({
  limit: 30,
  remaining: 29,
  reset: Date.now() + 60000,
  success: true,
});

const mockSlidingWindow = vi.fn(() => ({}));
const RATELIMIT_MOCK = vi.fn(function RatelimitMock() {
  return {
    limit: mockLimitFn,
  };
}) as unknown as {
  new (...args: unknown[]): { limit: ReturnType<typeof vi.fn> };
  slidingWindow: typeof mockSlidingWindow;
};
(RATELIMIT_MOCK as { slidingWindow: typeof mockSlidingWindow }).slidingWindow =
  mockSlidingWindow;

vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: RATELIMIT_MOCK,
}));

vi.mock("@upstash/redis", () => ({
  Redis: {
    fromEnv: vi.fn(() => ({})),
  },
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn((key: string) => {
    if (key === "UPSTASH_REDIS_REST_URL" || key === "UPSTASH_REDIS_REST_TOKEN") {
      return "test-value";
    }
    return "test-key";
  }),
}));

const mockGetUser = vi.fn();
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: mockGetUser,
    },
  })),
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

describe("/api/calendar/freebusy route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLimitFn.mockResolvedValue({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60000,
      success: true,
    });
    mockGetUser.mockResolvedValue({
      data: { user: { id: "user-1" } },
      error: null,
    });
    mockQueryFreeBusy.mockResolvedValue({
      calendars: {
        primary: {
          busy: [
            {
              end: "2025-01-15T11:00:00Z",
              start: "2025-01-15T10:00:00Z",
            },
          ],
        },
      },
      kind: "calendar#freeBusy",
      timeMax: new Date("2025-01-16T00:00:00Z"),
      timeMin: new Date("2025-01-15T00:00:00Z"),
    });
  });

  it("queries free/busy successfully", async () => {
    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.calendars).toBeDefined();
    expect(body.calendars.primary).toBeDefined();
  });

  it("returns 400 on invalid request", async () => {
    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        // Missing required fields
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("returns 400 on empty items array", async () => {
    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("returns 401 when unauthenticated", async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: null },
      error: { message: "Unauthorized" },
    });

    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req);
    expect(res.status).toBe(401);
  });

  it("handles empty busy periods", async () => {
    mockQueryFreeBusy.mockResolvedValueOnce({
      calendars: {
        primary: {
          busy: [],
        },
      },
      kind: "calendar#freeBusy",
      timeMax: new Date("2025-01-16T00:00:00Z"),
      timeMin: new Date("2025-01-15T00:00:00Z"),
    });

    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.calendars.primary.busy).toEqual([]);
  });

  it("returns 429 on rate limit", async () => {
    mockLimitFn.mockResolvedValueOnce({
      limit: 30,
      remaining: 0,
      reset: Date.now() + 60000,
      success: false,
    });

    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req);
    expect(res.status).toBe(429);
  });
});
