/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  enableApiRouteRateLimit,
  mockApiRouteRateLimitOnce,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";

const mockCalendars = {
  items: [
    {
      accessRole: "owner",
      defaultReminders: [],
      deleted: false,
      description: "My primary calendar",
      hidden: false,
      id: "primary",
      kind: "calendar#calendarListEntry" as const,
      primary: true,
      selected: true,
      summary: "Primary Calendar",
      timeZone: "America/New_York",
    },
  ],
  kind: "calendar#calendarList" as const,
};

const MOCK_GOOGLE_CALENDAR_API_ERROR = vi.hoisted(
  () =>
    class MockGoogleCalendarApiError extends Error {
      statusCode: number;

      constructor(message: string, statusCode: number) {
        super(message);
        this.name = "GoogleCalendarApiError";
        this.statusCode = statusCode;
      }
    }
);

vi.mock("@/lib/calendar/google", () => ({
  GoogleCalendarApiError: MOCK_GOOGLE_CALENDAR_API_ERROR,
  listCalendars: vi.fn(async () => mockCalendars),
}));

vi.mock("@/lib/calendar/auth", () => ({
  hasGoogleCalendarScopes: vi.fn(async () => true),
}));

describe("/api/calendar/status route", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    resetApiRouteMocks();
    const { listCalendars } = await import("@/lib/calendar/google");
    const { hasGoogleCalendarScopes } = await import("@/lib/calendar/auth");
    vi.mocked(listCalendars).mockReset();
    vi.mocked(listCalendars).mockResolvedValue(mockCalendars);
    vi.mocked(hasGoogleCalendarScopes).mockReset();
    vi.mocked(hasGoogleCalendarScopes).mockResolvedValue(true);
  });

  it("returns connected status with calendars", async () => {
    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.connected).toBe(true);
    expect(body.calendars).toHaveLength(1);
    expect(body.calendars[0].id).toBe("primary");
  });

  it("returns not connected when no token", async () => {
    const { hasGoogleCalendarScopes } = await import("@/lib/calendar/auth");

    vi.mocked(hasGoogleCalendarScopes).mockResolvedValueOnce(false);

    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.connected).toBe(false);
  });

  it("returns a 200 domain status when Google Calendar token expired", async () => {
    const { listCalendars } = await import("@/lib/calendar/google");

    vi.mocked(listCalendars).mockRejectedValueOnce(
      new MOCK_GOOGLE_CALENDAR_API_ERROR("expired", 401)
    );

    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    const body = (await res.json()) as { connected: boolean; message: string };

    expect(res.status).toBe(200);
    expect(body).toEqual({
      connected: false,
      message: "Google Calendar token expired. Please reconnect your account.",
    });
  });

  it("returns a 200 domain status when Google Calendar scopes are insufficient", async () => {
    const { listCalendars } = await import("@/lib/calendar/google");

    vi.mocked(listCalendars).mockRejectedValueOnce(
      new MOCK_GOOGLE_CALENDAR_API_ERROR("forbidden", 403)
    );

    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    const body = (await res.json()) as { connected: boolean; message: string };

    expect(res.status).toBe(200);
    expect(body).toEqual({
      connected: false,
      message: "Insufficient permissions. Please reconnect with calendar access.",
    });
  });

  it("returns 429 on rate limit exceeded", async () => {
    enableApiRouteRateLimit();
    mockApiRouteRateLimitOnce({
      remaining: 0,
      success: false,
    });

    const mod = await import("../status/route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });

    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(429);
  });
});
