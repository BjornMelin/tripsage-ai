/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  enableApiRouteRateLimit,
  mockApiRouteAuthUser,
  mockApiRouteRateLimitOnce,
  resetApiRouteMocks,
} from "@/test/api-route-helpers";
import { createMockNextRequest, createRouteParamsContext } from "@/test/route-helpers";

const mockQueryFreeBusy = vi.fn();
vi.mock("@/lib/calendar/google", () => ({
  queryFreeBusy: mockQueryFreeBusy,
}));

describe("/api/calendar/freebusy route", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    vi.clearAllMocks();
    mockApiRouteAuthUser({ id: "user-1" });
    mockQueryFreeBusy.mockResolvedValue({
      calendars: {
        primary: {
          busy: [
            {
              end: "2025-01-15T11:00:00Z",
              start: "2025-01-15T10:00:00Z",
            },
          ],
        },
      },
      kind: "calendar#freeBusy",
      timeMax: new Date("2025-01-16T00:00:00Z"),
      timeMin: new Date("2025-01-15T00:00:00Z"),
    });
  });

  it("queries free/busy successfully", async () => {
    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.calendars).toBeDefined();
    expect(body.calendars.primary).toBeDefined();
  });

  it("returns 400 on invalid request", async () => {
    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        // Missing required fields
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
  });

  it("returns 400 on empty items array", async () => {
    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(400);
  });

  it("returns 401 when unauthenticated", async () => {
    mockApiRouteAuthUser(null);

    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(401);
  });

  it("handles empty busy periods", async () => {
    mockQueryFreeBusy.mockResolvedValueOnce({
      calendars: {
        primary: {
          busy: [],
        },
      },
      kind: "calendar#freeBusy",
      timeMax: new Date("2025-01-16T00:00:00Z"),
      timeMin: new Date("2025-01-15T00:00:00Z"),
    });

    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.calendars.primary.busy).toEqual([]);
  });

  it("returns 429 on rate limit", async () => {
    enableApiRouteRateLimit();
    mockApiRouteRateLimitOnce({
      remaining: 0,
      success: false,
    });

    const mod = await import("../freebusy/route");
    const req = createMockNextRequest({
      body: {
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      },
      method: "POST",
      url: "http://localhost/api/calendar/freebusy",
    });

    const res = await mod.POST(req, createRouteParamsContext());
    expect(res.status).toBe(429);
  });
});
