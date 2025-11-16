/**
 * @vitest-environment node
 */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as googleCalendar from "@/lib/calendar/google";

// Mock Supabase before importing route handlers
const mockUser = { email: "test@example.com", id: "user-1" };
const mockSupabase = {
  auth: {
    getUser: vi.fn(async () => ({
      data: { user: mockUser },
      error: null,
    })),
  },
};

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => mockSupabase),
}));

// Mock rate limiters to return undefined (disabled)
vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: vi.fn(),
}));
vi.mock("@upstash/redis", () => ({
  Redis: { fromEnv: vi.fn(() => ({})) },
}));

// Mock env helpers
vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn(() => undefined),
}));

// Import route handlers after mocks
import * as eventsRoute from "../events/route";

describe("/api/calendar/events route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: mockUser },
      error: null,
    });
    vi.spyOn(googleCalendar, "listEvents").mockResolvedValue({
      items: [
        {
          end: { dateTime: "2025-07-15T11:00:00Z" },
          id: "event-1",
          start: { dateTime: "2025-07-15T10:00:00Z" },
          summary: "Test Event",
        },
      ],
    } as never);
    vi.spyOn(googleCalendar, "createEvent").mockResolvedValue({
      id: "event-new",
      summary: "New Event",
    } as never);
    vi.spyOn(googleCalendar, "updateEvent").mockResolvedValue({
      id: "event-updated",
      summary: "Updated Event",
    } as never);
    vi.spyOn(googleCalendar, "deleteEvent").mockResolvedValue(undefined);
  });

  describe("GET", () => {
    it("returns 401 when unauthenticated", async () => {
      mockSupabase.auth.getUser.mockResolvedValueOnce({
        data: { user: null },
        error: { message: "Unauthorized" },
      } as never);

      const req = new Request("http://localhost/api/calendar/events", {
        method: "GET",
      }) as NextRequest;

      const res = await eventsRoute.GET(req);
      expect(res.status).toBe(401);
      const json = await res.json();
      expect(json.error).toBe("Unauthorized");
    });

    it("lists events successfully", async () => {
      const req = new Request("http://localhost/api/calendar/events", {
        method: "GET",
      }) as NextRequest;

      const res = await eventsRoute.GET(req);
      expect(res.status).toBe(200);
      const json = await res.json();
      expect(json.items).toHaveLength(1);
      expect(json.items[0].summary).toBe("Test Event");
    });

    it("returns 400 on invalid query parameters", async () => {
      const req = new Request(
        "http://localhost/api/calendar/events?maxResults=invalid",
        {
          method: "GET",
        }
      ) as NextRequest;

      const res = await eventsRoute.GET(req);
      expect(res.status).toBe(400);
    });
  });

  describe("POST", () => {
    it("creates event successfully", async () => {
      const req = new Request("http://localhost/api/calendar/events", {
        body: JSON.stringify({
          end: { dateTime: "2025-07-15T11:00:00Z" },
          start: { dateTime: "2025-07-15T10:00:00Z" },
          summary: "New Event",
        }),
        headers: { "content-type": "application/json" },
        method: "POST",
      }) as NextRequest;

      const res = await eventsRoute.POST(req);
      expect(res.status).toBe(201);
      const json = await res.json();
      expect(json.id).toBe("event-new");
      expect(googleCalendar.createEvent).toHaveBeenCalled();
    });

    it("returns 400 on invalid request body", async () => {
      const req = new Request("http://localhost/api/calendar/events", {
        body: JSON.stringify({ invalid: "data" }),
        headers: { "content-type": "application/json" },
        method: "POST",
      }) as NextRequest;

      const res = await eventsRoute.POST(req);
      expect(res.status).toBe(400);
    });
  });

  describe("PATCH", () => {
    it("updates event successfully", async () => {
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        body: JSON.stringify({
          summary: "Updated Event",
        }),
        headers: { "content-type": "application/json" },
        method: "PATCH",
      }) as NextRequest;

      const res = await eventsRoute.PATCH(req);
      expect(res.status).toBe(200);
      const json = await res.json();
      expect(json.id).toBe("event-updated");
      expect(googleCalendar.updateEvent).toHaveBeenCalled();
    });

    it("returns 400 when eventId missing", async () => {
      const req = new Request("http://localhost/api/calendar/events", {
        body: JSON.stringify({ summary: "Updated" }),
        headers: { "content-type": "application/json" },
        method: "PATCH",
      }) as NextRequest;

      const res = await eventsRoute.PATCH(req);
      expect(res.status).toBe(400);
    });
  });

  describe("DELETE", () => {
    it("deletes event successfully", async () => {
      const req = new Request("http://localhost/api/calendar/events?eventId=event-1", {
        method: "DELETE",
      }) as NextRequest;

      const res = await eventsRoute.DELETE(req);
      expect(res.status).toBe(200);
      const json = await res.json();
      expect(json.success).toBe(true);
      expect(googleCalendar.deleteEvent).toHaveBeenCalled();
    });

    it("returns 400 when eventId missing", async () => {
      const req = new Request("http://localhost/api/calendar/events", {
        method: "DELETE",
      }) as NextRequest;

      const res = await eventsRoute.DELETE(req);
      expect(res.status).toBe(400);
    });
  });
});
