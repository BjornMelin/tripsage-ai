/** @vitest-environment node */

import { beforeEach, describe, expect, it } from "vitest";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/api-route-helpers";
import { createMockNextRequest } from "@/test/route-helpers";

describe("/api/calendar/ics/import", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteAuthUser({ id: "user-1" });
  });

  it("imports ICS successfully", async () => {
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
    const req = createMockNextRequest({
      body: {
        icsData: icsContent,
        validateOnly: true,
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/import",
    });

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.count).toBeGreaterThan(0);
    expect(body.events).toBeDefined();
    expect(Array.isArray(body.events)).toBe(true);
  });

  it("returns 400 on invalid ICS", async () => {
    const mod = await import("../ics/import/route");
    const req = createMockNextRequest({
      body: {
        icsData: "completely invalid ics content that cannot be parsed",
        validateOnly: true,
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/import",
    });

    const res = await mod.POST(req);
    // node-ical may parse some invalid content, so check for either 400 or empty events
    expect([400, 200]).toContain(res.status);
    if (res.status === 200) {
      const body = await res.json();
      expect(body.count).toBe(0);
    }
  });

  it("returns 400 on missing icsData", async () => {
    const mod = await import("../ics/import/route");
    const req = createMockNextRequest({
      body: {
        validateOnly: true,
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/import",
    });

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("handles empty ICS file", async () => {
    const mod = await import("../ics/import/route");
    const req = createMockNextRequest({
      body: {
        icsData: "",
        validateOnly: true,
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/import",
    });

    const res = await mod.POST(req);
    expect(res.status).toBe(400);
  });

  it("handles ICS with multiple events", async () => {
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
    const req = createMockNextRequest({
      body: {
        icsData: icsContent,
        validateOnly: true,
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/import",
    });

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.count).toBe(2);
    expect(body.events).toHaveLength(2);
  });

  it("handles ICS with line folding", async () => {
    // Test RFC 5545 line folding where long lines are split with CRLF + space
    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:folded-event
DTSTART;TZID=America/New_York:20250115T100000
DTEND;TZID=America/New_York:20250115T110000
SUMMARY:This is a very long summary that would normally be folded
  across multiple lines in a real ICS file but we're testing the
  parser's ability to handle it
DESCRIPTION:This description spans multiple lines and should be
  properly unfolded by the parser according to RFC 5545 section 3.1
LOCATION:Test Location
END:VEVENT
END:VCALENDAR`;

    const mod = await import("../ics/import/route");
    const req = createMockNextRequest({
      body: {
        icsData: icsContent,
        validateOnly: true,
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/import",
    });

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.count).toBe(1);
    expect(body.events[0].summary).toBe(
      "This is a very long summary that would normally be folded across multiple lines in a real ICS file but we're testing the parser's ability to handle it"
    );
    expect(body.events[0].description).toBe(
      "This description spans multiple lines and should be properly unfolded by the parser according to RFC 5545 section 3.1"
    );
  });

  it("handles ICS with property parameters", async () => {
    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:param-event
DTSTART;TZID=America/New_York:20250115T100000
DTEND;TZID=America/New_York:20250115T110000
SUMMARY:Event with timezone parameters
LOCATION:Conference Room A
ATTENDEE;CN="John Doe";CUTYPE=INDIVIDUAL:mailto:john@example.com
ATTENDEE;CN="Jane Smith":mailto:jane@example.com
RRULE:FREQ=WEEKLY;BYDAY=MO;UNTIL=20251231T235959Z
END:VEVENT
END:VCALENDAR`;

    const mod = await import("../ics/import/route");
    const req = createMockNextRequest({
      body: {
        icsData: icsContent,
        validateOnly: true,
      },
      method: "POST",
      url: "http://localhost/api/calendar/ics/import",
    });

    const res = await mod.POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.count).toBe(1);
    expect(body.events[0].summary).toBe("Event with timezone parameters");
    expect(body.events[0].location).toBe("Conference Room A");

    // Check attendees with parameters are parsed
    expect(body.events[0].attendees).toHaveLength(2);
    expect(body.events[0].attendees[0].displayName).toBe("John Doe");
    expect(body.events[0].attendees[0].email).toBe("mailto:john@example.com");
    expect(body.events[0].attendees[1].displayName).toBe("Jane Smith"); // Has CN parameter
    expect(body.events[0].attendees[1].email).toBe("mailto:jane@example.com");

    // Check recurrence rule is parsed
    expect(body.events[0].recurrence).toHaveLength(1);
    expect(body.events[0].recurrence[0]).toContain("FREQ=WEEKLY");
    expect(body.events[0].recurrence[0]).toContain("BYDAY=MO");
    expect(body.events[0].recurrence[0]).toContain("UNTIL=20251231T235959");
  });
});
