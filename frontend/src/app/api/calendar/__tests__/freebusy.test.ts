import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/calendar/freebusy route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  const mockRateLimit = {
    limit: 30,
    remaining: 29,
    reset: Date.now() + 60000,
    success: true,
  };

  const setupMocks = (overrides?: {
    rateLimit?: typeof mockRateLimit;
    googleFreeBusy?: unknown;
  }) => {
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
      queryFreeBusy: vi.fn(
        async () =>
          overrides?.googleFreeBusy || {
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
          }
      ),
    }));

    vi.doMock("@upstash/ratelimit", () => {
      const slidingWindow = vi.fn(() => ({}));
      const rateLimitResult = overrides?.rateLimit || mockRateLimit;
      const ctor = vi.fn(function RatelimitMock() {
        return {
          limit: vi.fn().mockResolvedValue(rateLimitResult),
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
  };

  it("queries free/busy successfully", async () => {
    setupMocks();

    const mod = await import("../freebusy/route");
    const req = new Request("http://localhost/api/calendar/freebusy", {
      body: JSON.stringify({
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.calendars).toBeDefined();
    expect(body.calendars.primary).toBeDefined();
  });

  it("returns 400 on invalid request", async () => {
    setupMocks();

    const mod = await import("../freebusy/route");
    const req = new Request("http://localhost/api/calendar/freebusy", {
      body: JSON.stringify({
        // Missing required fields
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("returns 400 on empty items array", async () => {
    setupMocks();

    const mod = await import("../freebusy/route");
    const req = new Request("http://localhost/api/calendar/freebusy", {
      body: JSON.stringify({
        items: [],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("returns 401 when unauthenticated", async () => {
    vi.doMock("@/lib/supabase/server", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: {
          getUser: async () => ({
            data: { user: null },
            error: { message: "Unauthorized" },
          }),
        },
      })),
    }));

    const mod = await import("../freebusy/route");
    const req = new Request("http://localhost/api/calendar/freebusy", {
      body: JSON.stringify({
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(401);
  });

  it("handles empty busy periods", async () => {
    setupMocks({
      googleFreeBusy: {
        calendars: {
          primary: {
            busy: [],
          },
        },
        kind: "calendar#freeBusy",
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
    });

    const mod = await import("../freebusy/route");
    const req = new Request("http://localhost/api/calendar/freebusy", {
      body: JSON.stringify({
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.calendars.primary.busy).toEqual([]);
  });

  it("returns 429 on rate limit", async () => {
    setupMocks({
      rateLimit: {
        ...mockRateLimit,
        remaining: 0,
        success: false,
      },
    });

    const mod = await import("../freebusy/route");
    const req = new Request("http://localhost/api/calendar/freebusy", {
      body: JSON.stringify({
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(429);
  });
});
