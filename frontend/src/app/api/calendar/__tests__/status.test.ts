import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/calendar/status route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("returns connected status with calendars", async () => {
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

    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: {
          getUser: async () => ({
            data: { user: { id: "user-1" } },
            error: null,
          }),
        },
      })),
    }));

    vi.doMock("@/lib/calendar/google", () => ({
      listCalendars: vi.fn(async () => mockCalendars),
    }));

    vi.doMock("@/lib/calendar/auth", () => ({
      hasGoogleCalendarScopes: vi.fn(async () => true),
    }));

    vi.doMock("@upstash/ratelimit", () => {
      const slidingWindow = vi.fn(() => ({}));
      const ctor = vi.fn(function RatelimitMock() {
        return {
          limit: vi.fn().mockResolvedValue({
            limit: 60,
            remaining: 59,
            reset: Date.now() + 60000,
            success: true,
          }),
        };
      }) as unknown as {
        new (...args: unknown[]): { limit: ReturnType<typeof vi.fn> };
        slidingWindow: typeof slidingWindow;
      };
      ctor.slidingWindow = slidingWindow;
      return { Ratelimit: ctor };
    });

    vi.doMock("@upstash/redis", () => ({
      Redis: {
        fromEnv: vi.fn(() => ({})),
      },
    }));

    vi.doMock("@/lib/env/server", () => ({
      getServerEnvVarWithFallback: vi.fn(() => "test-key"),
    }));

    const mod = await import("../status/route");
    const req = new Request("http://localhost/api/calendar/status", {
      method: "GET",
    }) as unknown as NextRequest;

    const res = await mod.GET(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.connected).toBe(true);
    expect(body.calendars).toHaveLength(1);
    expect(body.calendars[0].id).toBe("primary");
  });

  it("returns not connected when no token", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: {
          getUser: async () => ({
            data: { user: { id: "user-1" } },
            error: null,
          }),
        },
      })),
    }));

    vi.doMock("@/lib/calendar/google", () => ({
      listCalendars: vi.fn(() => {
        throw new Error("No token");
      }),
    }));

    vi.doMock("@/lib/calendar/auth", () => ({
      hasGoogleCalendarScopes: vi.fn(async () => false),
    }));

    vi.doMock("@upstash/ratelimit", () => {
      const slidingWindow = vi.fn(() => ({}));
      const ctor = vi.fn(function RatelimitMock() {
        return {
          limit: vi.fn().mockResolvedValue({
            limit: 60,
            remaining: 59,
            reset: Date.now() + 60000,
            success: true,
          }),
        };
      }) as unknown as {
        new (...args: unknown[]): { limit: ReturnType<typeof vi.fn> };
        slidingWindow: typeof slidingWindow;
      };
      ctor.slidingWindow = slidingWindow;
      return { Ratelimit: ctor };
    });

    vi.doMock("@upstash/redis", () => ({
      Redis: {
        fromEnv: vi.fn(() => ({})),
      },
    }));

    vi.doMock("@/lib/env/server", () => ({
      getServerEnvVarWithFallback: vi.fn(() => "test-key"),
    }));

    const mod = await import("../status/route");
    const req = new Request("http://localhost/api/calendar/status", {
      method: "GET",
    }) as unknown as NextRequest;

    const res = await mod.GET(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.connected).toBe(false);
  });

  it("returns 429 on rate limit exceeded", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: {
          getUser: async () => ({
            data: { user: { id: "user-1" } },
            error: null,
          }),
        },
      })),
    }));

    vi.doMock("@upstash/ratelimit", () => {
      const slidingWindow = vi.fn(() => ({}));
      const ctor = vi.fn(function RatelimitMock() {
        return {
          limit: vi.fn().mockResolvedValue({
            limit: 60,
            remaining: 0,
            reset: Date.now() + 60000,
            success: false,
          }),
        };
      }) as unknown as {
        new (...args: unknown[]): { limit: ReturnType<typeof vi.fn> };
        slidingWindow: typeof slidingWindow;
      };
      ctor.slidingWindow = slidingWindow;
      return { Ratelimit: ctor };
    });

    vi.doMock("@upstash/redis", () => ({
      Redis: {
        fromEnv: vi.fn(() => ({})),
      },
    }));

    vi.doMock("@/lib/env/server", () => ({
      getServerEnvVarWithFallback: vi.fn(() => "test-key"),
    }));

    const mod = await import("../status/route");
    const req = new Request("http://localhost/api/calendar/status", {
      method: "GET",
    }) as unknown as NextRequest;

    const res = await mod.GET(req);
    expect(res.status).toBe(429);
  });
});
