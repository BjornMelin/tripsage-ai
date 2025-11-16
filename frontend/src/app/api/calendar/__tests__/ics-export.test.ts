/**
 * @vitest-environment node
 */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
import * as icsExportRoute from "../ics/export/route";

describe("/api/calendar/ics/export route", () => {
  const mockEvent = {
    description: "Test description",
    end: { dateTime: new Date("2025-07-15T11:00:00Z") },
    location: "Test Location",
    start: { dateTime: new Date("2025-07-15T10:00:00Z") },
    summary: "Test Event",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockSupabase.auth.getUser.mockResolvedValue({
      data: { user: mockUser },
      error: null,
    });
  });

  it("exports ICS successfully", async () => {
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [mockEvent],
      }),
      headers: { "content-type": "application/json" },
      method: "POST",
    }) as NextRequest;

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("text/calendar; charset=utf-8");
    expect(res.headers.get("Content-Disposition")).toContain("Test_Calendar.ics");
    const text = await res.text();
    expect(text).toContain("BEGIN:VCALENDAR");
    expect(text).toContain("BEGIN:VEVENT");
    expect(text).toContain("Test Event");
  });

  it("returns 401 when unauthenticated", async () => {
    mockSupabase.auth.getUser.mockResolvedValueOnce({
      data: { user: null },
      error: { message: "Unauthorized" },
    } as never);

    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [mockEvent],
      }),
      headers: { "content-type": "application/json" },
      method: "POST",
    }) as NextRequest;

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.error).toBe("Unauthorized");
  });

  it("returns 400 on invalid request body", async () => {
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [],
      }),
      headers: { "content-type": "application/json" },
      method: "POST",
    }) as NextRequest;

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toBe("Invalid request body");
  });

  it("returns 400 on empty events array", async () => {
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [],
      }),
      headers: { "content-type": "application/json" },
      method: "POST",
    }) as NextRequest;

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(400);
  });

  it("includes custom timezone in ICS", async () => {
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [mockEvent],
        timezone: "America/New_York",
      }),
      headers: { "content-type": "application/json" },
      method: "POST",
    }) as NextRequest;

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(200);
    const text = await res.text();
    expect(text).toContain("America/New_York");
  });

  it("exports ICS with multiple events", async () => {
    const req = new Request("http://localhost/api/calendar/ics/export", {
      body: JSON.stringify({
        calendarName: "Test Calendar",
        events: [
          mockEvent,
          {
            ...mockEvent,
            end: { dateTime: new Date("2025-07-16T11:00:00Z") },
            start: { dateTime: new Date("2025-07-16T10:00:00Z") },
            summary: "Second Event",
          },
        ],
      }),
      headers: { "content-type": "application/json" },
      method: "POST",
    }) as NextRequest;

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(200);
    const text = await res.text();
    const eventMatches = text.match(/BEGIN:VEVENT/g);
    expect(eventMatches).toHaveLength(2);
  });
});
