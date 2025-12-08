/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setSupabaseFactoryForTests } from "@/lib/api/factory";
import * as googleCalendar from "@/lib/calendar/google";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

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

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

// Mock env helpers
vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn(() => undefined),
}));

// Mock route helpers
vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

// Import route handlers after mocks
import * as eventsRoute from "../events/route";

describe("/api/calendar/events", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setSupabaseFactoryForTests(async () => mockSupabase as never);
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

  afterEach(() => {
    setSupabaseFactoryForTests(null);
  });

  describe("GET", () => {
    it("returns 401 when unauthenticated", async () => {
      mockSupabase.auth.getUser.mockResolvedValueOnce({
        data: { user: null },
        error: { message: "Unauthorized" },
      } as never);

      const req = createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/calendar/events",
      });

      const res = await eventsRoute.GET(req, createRouteParamsContext());
      expect(res.status).toBe(401);
      const json = await res.json();
      expect(json.error).toBe("unauthorized");
    });

    it("lists events successfully", async () => {
      const req = createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/calendar/events",
      });

      const res = await eventsRoute.GET(req, createRouteParamsContext());
      expect(res.status).toBe(200);
      const json = await res.json();
      expect(json.items).toHaveLength(1);
      expect(json.items[0].summary).toBe("Test Event");
    });

    it("returns 400 on invalid query parameters", async () => {
      const req = createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/calendar/events?maxResults=invalid",
      });

      const res = await eventsRoute.GET(req, createRouteParamsContext());
      expect(res.status).toBe(400);
    });
  });

  describe("POST", () => {
    it("creates event successfully", async () => {
      const req = createMockNextRequest({
        body: {
          end: { dateTime: "2025-07-15T11:00:00Z" },
          start: { dateTime: "2025-07-15T10:00:00Z" },
          summary: "New Event",
        },
        method: "POST",
        url: "http://localhost/api/calendar/events",
      });

      const res = await eventsRoute.POST(req, createRouteParamsContext());
      expect(res.status).toBe(201);
      const json = await res.json();
      expect(json.id).toBe("event-new");
      expect(googleCalendar.createEvent).toHaveBeenCalled();
    });

    it("returns 400 on invalid request body", async () => {
      const req = createMockNextRequest({
        body: { invalid: "data" },
        method: "POST",
        url: "http://localhost/api/calendar/events",
      });

      const res = await eventsRoute.POST(req, createRouteParamsContext());
      expect(res.status).toBe(400);
    });
  });

  describe("PATCH", () => {
    it("updates event successfully", async () => {
      const req = createMockNextRequest({
        body: {
          summary: "Updated Event",
        },
        method: "PATCH",
        url: "http://localhost/api/calendar/events?eventId=event-1",
      });

      const res = await eventsRoute.PATCH(req, createRouteParamsContext());
      expect(res.status).toBe(200);
      const json = await res.json();
      expect(json.id).toBe("event-updated");
      expect(googleCalendar.updateEvent).toHaveBeenCalled();
    });

    it("returns 400 when eventId missing", async () => {
      const req = createMockNextRequest({
        body: { summary: "Updated" },
        method: "PATCH",
        url: "http://localhost/api/calendar/events",
      });

      const res = await eventsRoute.PATCH(req, createRouteParamsContext());
      expect(res.status).toBe(400);
    });
  });

  describe("DELETE", () => {
    it("deletes event successfully", async () => {
      const req = createMockNextRequest({
        method: "DELETE",
        url: "http://localhost/api/calendar/events?eventId=event-1",
      });

      const res = await eventsRoute.DELETE(req, createRouteParamsContext());
      expect(res.status).toBe(200);
      const json = await res.json();
      expect(json.success).toBe(true);
      expect(googleCalendar.deleteEvent).toHaveBeenCalled();
    });

    it("returns 400 when eventId missing", async () => {
      const req = createMockNextRequest({
        method: "DELETE",
        url: "http://localhost/api/calendar/events",
      });

      const res = await eventsRoute.DELETE(req, createRouteParamsContext());
      expect(res.status).toBe(400);
    });
  });
});
