/** @vitest-environment node */

import { beforeEach, describe, expect, it } from "vitest";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/api-route-helpers";
import { createMockNextRequest } from "@/test/route-helpers";
import * as icsExportRoute from "../ics/export/route";

describe("/api/calendar/ics/export", () => {
  const mockEvent = {
    description: "Test description",
    end: { dateTime: new Date("2025-07-15T11:00:00Z") },
    location: "Test Location",
    start: { dateTime: new Date("2025-07-15T10:00:00Z") },
    summary: "Test Event",
  };

  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
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
    mockApiRouteAuthUser(null);

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
    expect(json.error).toBe("unauthorized");
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
    expect(json.error).toBe("BAD_REQUEST");
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
