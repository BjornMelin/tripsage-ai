import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("/api/calendar/events route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  const mockRateLimit = {
    limit: 60,
    remaining: 59,
    reset: Date.now() + 60000,
    success: true,
  };

  const mockSupabase = {
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
        error: null,
      }),
    },
  };

  const setupMocks = (overrides?: {
    rateLimit?: typeof mockRateLimit;
    googleListEvents?: unknown;
    googleCreateEvent?: unknown;
    googleUpdateEvent?: unknown;
    googleDeleteEvent?: unknown;
  }) => {
    vi.doMock("@/lib/supabase", () => ({
      createServerSupabase: vi.fn(async () => mockSupabase),
    }));

    vi.doMock("@/lib/calendar/google", () => ({
      createEvent: vi.fn(
        async () =>
          overrides?.googleCreateEvent || {
            htmlLink: "https://calendar.google.com/event?eid=xyz",
            id: "event-new",
            summary: "New Event",
          }
      ),
      deleteEvent: vi.fn(async () => undefined),
      listEvents: vi.fn(
        async () =>
          overrides?.googleListEvents || {
            items: [
              {
                end: { dateTime: new Date().toISOString() },
                id: "event-1",
                start: { dateTime: new Date().toISOString() },
                summary: "Test Event",
              },
            ],
            kind: "calendar#events",
          }
      ),
      updateEvent: vi.fn(
        async () =>
          overrides?.googleUpdateEvent || {
            id: "event-1",
            summary: "Updated Event",
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

  describe("GET", () => {
    it("lists events successfully", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request(
        "http://localhost/api/calendar/events?calendarId=primary",
        {
          method: "GET",
        }
      ) as unknown as NextRequest;

      const res = await mod.GET(req);
      const body = await res.json();

      expect(res.status).toBe(200);
      expect(body.items).toBeDefined();
      expect(Array.isArray(body.items)).toBe(true);
    });

    it("handles query parameters", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const timeMin = new Date("2025-01-15").toISOString();
      const timeMax = new Date("2025-01-20").toISOString();
      const req = new Request(
        `http://localhost/api/calendar/events?timeMin=${timeMin}&timeMax=${timeMax}&maxResults=10`,
        {
          method: "GET",
        }
      ) as unknown as NextRequest;

      const res = await mod.GET(req);
      expect(res.status).toBe(200);
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

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        method: "GET",
      }) as unknown as NextRequest;

      const res = await mod.GET(req);
      expect(res.status).toBe(401);
    });

    it("handles empty events list", async () => {
      setupMocks({
        googleListEvents: {
          items: [],
          kind: "calendar#events",
        },
      });

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        method: "GET",
      }) as unknown as NextRequest;

      const res = await mod.GET(req);
      const body = await res.json();

      expect(res.status).toBe(200);
      expect(body.items).toEqual([]);
    });

    it("handles Google API errors", async () => {
      setupMocks();

      vi.doMock("@/lib/calendar/google", () => ({
        listEvents: vi.fn().mockRejectedValue(new Error("Google API error")),
      }));

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        method: "GET",
      }) as unknown as NextRequest;

      const res = await mod.GET(req);
      expect(res.status).toBe(500);
    });

    it("returns 429 on rate limit", async () => {
      setupMocks({
        rateLimit: {
          ...mockRateLimit,
          remaining: 0,
          success: false,
        },
      });

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        method: "GET",
      }) as unknown as NextRequest;

      const res = await mod.GET(req);
      expect(res.status).toBe(429);
    });
  });

  describe("POST", () => {
    it("creates event successfully", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        body: JSON.stringify({
          end: { dateTime: new Date(Date.now() + 3600000).toISOString() },
          start: { dateTime: new Date().toISOString() },
          summary: "New Event",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      }) as unknown as NextRequest;

      const res = await mod.POST(req);
      const body = await res.json();

      expect(res.status).toBe(201);
      expect(body.id).toBe("event-new");
    });

    it("returns 400 on invalid request", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        body: JSON.stringify({
          // Missing required fields
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      }) as unknown as NextRequest;

      const res = await mod.POST(req);
      expect(res.status).toBe(400);
    });
  });

  describe("PATCH", () => {
    it("updates event successfully", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        body: JSON.stringify({
          summary: "Updated Event",
        }),
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      }) as unknown as NextRequest;

      const res = await mod.PATCH(req);
      const body = await res.json();

      expect(res.status).toBe(200);
      expect(body.summary).toBe("Updated Event");
    });

    it("returns 400 when eventId missing", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        body: JSON.stringify({
          summary: "Updated Event",
        }),
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      }) as unknown as NextRequest;

      const res = await mod.PATCH(req);
      expect(res.status).toBe(400);
    });

    it("handles partial update with only some fields", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        body: JSON.stringify({
          description: "Updated description only",
        }),
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      }) as unknown as NextRequest;

      const res = await mod.PATCH(req);
      expect(res.status).toBe(200);
    });

    it("handles Google API errors on update", async () => {
      setupMocks();

      vi.doMock("@/lib/calendar/google", () => ({
        updateEvent: vi.fn().mockRejectedValue(new Error("Google API error")),
      }));

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        body: JSON.stringify({
          summary: "Updated Event",
        }),
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      }) as unknown as NextRequest;

      const res = await mod.PATCH(req);
      expect(res.status).toBe(500);
    });
  });

  describe("DELETE", () => {
    it("deletes event successfully", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        method: "DELETE",
      }) as unknown as NextRequest;

      const res = await mod.DELETE(req);
      expect(res.status).toBe(200);
    });

    it("returns 400 when eventId missing", async () => {
      setupMocks();

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events", {
        method: "DELETE",
      }) as unknown as NextRequest;

      const res = await mod.DELETE(req);
      expect(res.status).toBe(400);
    });

    it("handles Google API errors on delete", async () => {
      setupMocks();

      vi.doMock("@/lib/calendar/google", () => ({
        deleteEvent: vi.fn().mockRejectedValue(new Error("Google API error")),
      }));

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        method: "DELETE",
      }) as unknown as NextRequest;

      const res = await mod.DELETE(req);
      expect(res.status).toBe(500);
    });

    it("returns 401 when unauthenticated on delete", async () => {
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

      const mod = await import("../events/route");
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        method: "DELETE",
      }) as unknown as NextRequest;

      const res = await mod.DELETE(req);
      expect(res.status).toBe(401);
    });
  });
});
