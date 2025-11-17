import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() before any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const mockCalendars = {
  items: [
    {
      accessRole: "owner",
      description: "My primary calendar",
      id: "primary",
      primary: true,
      summary: "Primary Calendar",
      timeZone: "America/New_York",
    },
  ],
  kind: "calendar#calendarList",
};

const mockLimitFn = vi.fn().mockResolvedValue({
  limit: 60,
  remaining: 59,
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

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
        error: null,
      }),
    },
  })),
}));

vi.mock("@/lib/calendar/google", () => ({
  listCalendars: vi.fn(async () => mockCalendars),
}));

vi.mock("@/lib/calendar/auth", () => ({
  hasGoogleCalendarScopes: vi.fn(async () => true),
}));

vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: RATELIMIT_MOCK,
}));

vi.mock("@upstash/redis", () => ({
  Redis: {
    fromEnv: vi.fn(() => ({})),
  },
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn(() => "test-key"),
}));

describe("/api/calendar/status route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLimitFn.mockResolvedValue({
      limit: 60,
      remaining: 59,
      reset: Date.now() + 60000,
      success: true,
    });
  });

  it("returns connected status with calendars", async () => {
    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.connected).toBe(true);
    expect(body.calendars).toHaveLength(1);
    expect(body.calendars[0].id).toBe("primary");
  });

  it("returns not connected when no token", async () => {
    const { listCalendars } = await import("@/lib/calendar/google");
    const { hasGoogleCalendarScopes } = await import("@/lib/calendar/auth");

    vi.mocked(listCalendars).mockRejectedValueOnce(new Error("No token"));
    vi.mocked(hasGoogleCalendarScopes).mockResolvedValueOnce(false);

    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.connected).toBe(false);
  });

  it("returns 429 on rate limit exceeded", async () => {
    mockLimitFn.mockResolvedValueOnce({
      limit: 60,
      remaining: 0,
      reset: Date.now() + 60000,
      success: false,
    });

    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req);
    expect(res.status).toBe(429);
  });
});
