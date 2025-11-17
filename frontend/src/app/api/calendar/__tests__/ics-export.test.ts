/**
 * @vitest-environment node
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

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
    const req = createMockNextRequest({
      body: {
        calendarName: "Test Calendar",
        events: [mockEvent],
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/export",
    });

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

    const req = createMockNextRequest({
      body: {
        calendarName: "Test Calendar",
        events: [mockEvent],
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/export",
    });

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.error).toBe("Unauthorized");
  });

  it("returns 400 on invalid request body", async () => {
    const req = createMockNextRequest({
      body: {
        calendarName: "Test Calendar",
        events: [],
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/export",
    });

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toBe("Invalid request body");
  });

  it("returns 400 on empty events array", async () => {
    const req = createMockNextRequest({
      body: {
        calendarName: "Test Calendar",
        events: [],
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/export",
    });

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(400);
  });

  it("includes custom timezone in ICS", async () => {
    const req = createMockNextRequest({
      body: {
        calendarName: "Test Calendar",
        events: [mockEvent],
        timezone: "America/New_York",
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/export",
    });

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(200);
    const text = await res.text();
    expect(text).toContain("America/New_York");
  });

  it("exports ICS with multiple events", async () => {
    const req = createMockNextRequest({
      body: {
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
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/export",
    });

    const res = await icsExportRoute.POST(req);
    expect(res.status).toBe(200);
    const text = await res.text();
    const eventMatches = text.match(/BEGIN:VEVENT/g);
    expect(eventMatches).toHaveLength(2);
  });
});
