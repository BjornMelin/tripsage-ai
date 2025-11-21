import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  enableApiRouteRateLimit,
  mockApiRouteRateLimitOnce,
  resetApiRouteMocks,
} from "@/test/api-route-helpers";
import { createMockNextRequest, createRouteParamsContext } from "@/test/route-helpers";

const mockCalendars = {
  items: [
    {
      accessRole: "owner",
      description: "My primary calendar",
      id: "primary",
      primary: true,
      summary: "Primary Calendar",
      timeZone: "America/New_York",
    },
  ],
  kind: "calendar#calendarList",
};

vi.mock("@/lib/calendar/google", () => ({
  listCalendars: vi.fn(async () => mockCalendars),
}));

vi.mock("@/lib/calendar/auth", () => ({
  hasGoogleCalendarScopes: vi.fn(async () => true),
}));

describe("/api/calendar/status route", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    vi.clearAllMocks();
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
    const { listCalendars } = await import("@/lib/calendar/google");
    const { hasGoogleCalendarScopes } = await import("@/lib/calendar/auth");

    vi.mocked(listCalendars).mockRejectedValueOnce(new Error("No token"));
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
