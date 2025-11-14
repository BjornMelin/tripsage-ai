import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/calendar/ics/export route", () => {
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

  const setupMocks = (overrides?: { rateLimit?: typeof mockRateLimit }) => {
    vi.doMock("@/lib/supabase", () => ({
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

  it("exports ICS successfully", async () => {
    setupMocks();

    const mod = await import("../ics/export/route");
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [
          {
            end: { dateTime: "2025-01-15T11:00:00.000Z" },
            start: { dateTime: "2025-01-15T10:00:00.000Z" },
            summary: "Test Event",
          },
        ],
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    const text = await res.text();

    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toContain("text/calendar");
    expect(text).toContain("BEGIN:VCALENDAR");
    expect(text).toContain("END:VCALENDAR");
  });

  it("returns 400 on invalid request", async () => {
    setupMocks();

    const mod = await import("../ics/export/route");
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        // Missing events
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("returns 400 on empty events array", async () => {
    setupMocks();

    const mod = await import("../ics/export/route");
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [],
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("returns 401 when unauthenticated", async () => {
    vi.doMock("@/lib/supabase", () => ({
      createServerSupabase: vi.fn(async () => ({
        auth: {
          getUser: async () => ({
            data: { user: null },
            error: { message: "Unauthorized" },
          }),
        },
      })),
    }));

    const mod = await import("../ics/export/route");
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [
          {
            end: { dateTime: "2025-01-15T11:00:00.000Z" },
            start: { dateTime: "2025-01-15T10:00:00.000Z" },
            summary: "Test Event",
          },
        ],
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(401);
  });

  it("exports ICS with multiple events", async () => {
    setupMocks();

    const mod = await import("../ics/export/route");
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [
          {
            end: { dateTime: "2025-01-15T11:00:00.000Z" },
            start: { dateTime: "2025-01-15T10:00:00.000Z" },
            summary: "Event 1",
          },
          {
            end: { dateTime: "2025-01-16T11:00:00.000Z" },
            start: { dateTime: "2025-01-16T10:00:00.000Z" },
            summary: "Event 2",
          },
        ],
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    const text = await res.text();

    expect(res.status).toBe(200);
    expect(text).toContain("Event 1");
    expect(text).toContain("Event 2");
  });

  it("includes custom timezone in ICS", async () => {
    setupMocks();

    const mod = await import("../ics/export/route");
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [
          {
            end: { dateTime: "2025-01-15T11:00:00.000Z" },
            start: { dateTime: "2025-01-15T10:00:00.000Z" },
            summary: "Test Event",
          },
        ],
        timezone: "America/New_York",
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    const text = await res.text();

    expect(res.status).toBe(200);
    expect(text).toContain("America/New_York");
  });

  it("returns 429 on rate limit", async () => {
    setupMocks({
      rateLimit: {
        ...mockRateLimit,
        remaining: 0,
        success: false,
      },
    });

    const mod = await import("../ics/export/route");
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [
          {
            end: { dateTime: "2025-01-15T11:00:00.000Z" },
            start: { dateTime: "2025-01-15T10:00:00.000Z" },
            summary: "Test Event",
          },
        ],
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(429);
  });
});
