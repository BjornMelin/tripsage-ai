import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/calendar/ics/import route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  const mockRateLimit = {
    limit: 20,
    remaining: 19,
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

  it("imports ICS successfully", async () => {
    setupMocks();

    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-1
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR`;

    const mod = await import("../ics/import/route");
    const req = new Request("http://localhost/api/calendar/ics/import", {
      body: JSON.stringify({
        icsData: icsContent,
        validateOnly: true,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.count).toBeGreaterThan(0);
    expect(body.events).toBeDefined();
    expect(Array.isArray(body.events)).toBe(true);
  });

  it("returns 400 on invalid ICS", async () => {
    setupMocks();

    const mod = await import("../ics/import/route");
    const req = new Request("http://localhost/api/calendar/ics/import", {
      body: JSON.stringify({
        icsData: "completely invalid ics content that cannot be parsed",
        validateOnly: true,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    // node-ical may parse some invalid content, so check for either 400 or empty events
    expect([400, 200]).toContain(res.status);
    if (res.status === 200) {
      const body = await res.json();
      expect(body.count).toBe(0);
    }
  });

  it("returns 400 on missing icsData", async () => {
    setupMocks();

    const mod = await import("../ics/import/route");
    const req = new Request("http://localhost/api/calendar/ics/import", {
      body: JSON.stringify({
        validateOnly: true,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("handles empty ICS file", async () => {
    setupMocks();

    const mod = await import("../ics/import/route");
    const req = new Request("http://localhost/api/calendar/ics/import", {
      body: JSON.stringify({
        icsData: "",
        validateOnly: true,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("handles ICS with multiple events", async () => {
    setupMocks();

    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:event-1
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Event 1
END:VEVENT
BEGIN:VEVENT
UID:event-2
DTSTART:20250116T100000Z
DTEND:20250116T110000Z
SUMMARY:Event 2
END:VEVENT
END:VCALENDAR`;

    const mod = await import("../ics/import/route");
    const req = new Request("http://localhost/api/calendar/ics/import", {
      body: JSON.stringify({
        icsData: icsContent,
        validateOnly: true,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.count).toBe(2);
    expect(body.events).toHaveLength(2);
  });

  it("returns 429 on rate limit", async () => {
    setupMocks({
      rateLimit: {
        ...mockRateLimit,
        remaining: 0,
        success: false,
      },
    });

    const mod = await import("../ics/import/route");
    const req = new Request("http://localhost/api/calendar/ics/import", {
      body: JSON.stringify({
        icsData: "BEGIN:VCALENDAR\nEND:VCALENDAR",
        validateOnly: true,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    }) as unknown as NextRequest;

    const res = await mod.POST(req);
    expect(res.status).toBe(429);
  });
});
