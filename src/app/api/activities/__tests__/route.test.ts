/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const MOCK_SUPABASE = vi.hoisted(() => ({
  auth: {
    getUser: vi.fn(),
  },
}));

const CREATE_SUPABASE = vi.hoisted(() => vi.fn(async () => MOCK_SUPABASE));

const MOCK_GET_REDIS = vi.hoisted(() => vi.fn(() => undefined));

const LIMIT_SPY = vi.hoisted(() => vi.fn());

const MOCK_SERVICE = vi.hoisted(() => ({
  details: vi.fn(),
  search: vi.fn(),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: MOCK_GET_REDIS,
}));

vi.mock("@upstash/ratelimit", () => {
  const slidingWindow = vi.fn(() => ({}));
  const ctor = vi.fn(function RatelimitMock() {
    return { limit: LIMIT_SPY };
  }) as unknown as {
    new (...args: unknown[]): { limit: ReturnType<typeof LIMIT_SPY> };
    slidingWindow: (...args: unknown[]) => unknown;
  };
  ctor.slidingWindow = slidingWindow as unknown as (...args: unknown[]) => unknown;
  return {
    Ratelimit: ctor,
    slidingWindow,
  };
});

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: CREATE_SUPABASE,
}));

vi.mock("@/lib/supabase/factory", () => ({
  getCurrentUser: vi.fn(async () => ({
    error: null,
    user: { id: "user-1" } as never,
  })),
}));

vi.mock("@domain/activities/container", () => ({
  getActivitiesService: vi.fn(() => MOCK_SERVICE),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  sanitizeAttributes: vi.fn((attrs) => attrs),
  withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
}));

vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    getTrustedRateLimitIdentifier: vi.fn((_req: NextRequest) => "user:user-1"),
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("/api/activities routes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    LIMIT_SPY.mockResolvedValue({ limit: 20, remaining: 10, reset: 0, success: true });
    CREATE_SUPABASE.mockResolvedValue(MOCK_SUPABASE);
    MOCK_SUPABASE.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-1" } },
      error: null,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("POST /api/activities/search", () => {
    it("should return activities on successful search", async () => {
      const mockResult = {
        activities: [
          {
            date: "2025-01-01",
            description: "Test",
            duration: 120,
            id: "places/1",
            location: "Test Location",
            name: "Test Activity",
            price: 2,
            rating: 4.5,
            type: "museum",
          },
        ],
        metadata: {
          cached: false,
          primarySource: "googleplaces" as const,
          sources: ["googleplaces" as const],
          total: 1,
        },
      };

      MOCK_SERVICE.search.mockResolvedValue(mockResult);

      const { POST } = await import("../search/route");
      const req = createMockNextRequest({
        body: { category: "museums", destination: "Paris" },
        method: "POST",
        url: "http://localhost/api/activities/search",
      });

      const res = await POST(req, createRouteParamsContext({}));
      const body = await res.json();

      expect(res.status).toBe(200);
      expect(body.activities).toHaveLength(1);
      expect(body.activities[0].name).toBe("Test Activity");
      expect(MOCK_SERVICE.search).toHaveBeenCalledWith(
        { category: "museums", destination: "Paris" },
        expect.objectContaining({ userId: "user-1" })
      );
    });

    it("should validate request body schema", async () => {
      const { POST } = await import("../search/route");
      // Use invalid data that violates schema constraints (e.g., negative numbers)
      const req = createMockNextRequest({
        body: { adults: -1, children: -5 },
        method: "POST",
        url: "http://localhost/api/activities/search",
      });

      const res = await POST(req, createRouteParamsContext({}));
      const body = await res.json();

      // Schema validation happens in the factory, should return 400
      expect(res.status).toBe(400);
      expect(body.error).toBe("invalid_request");
      expect(body.reason).toBeDefined();
    });

    it("should handle service errors", async () => {
      MOCK_SERVICE.search.mockRejectedValue(new Error("Service error"));

      const { POST } = await import("../search/route");
      const req = createMockNextRequest({
        body: { destination: "Paris" },
        method: "POST",
        url: "http://localhost/api/activities/search",
      });

      const res = await POST(req, createRouteParamsContext({}));
      const body = await res.json();

      expect(res.status).toBe(500);
      expect(body.error).toBe("internal");
    });

    it("should enforce rate limiting", async () => {
      LIMIT_SPY.mockResolvedValue({
        limit: 20,
        remaining: 0,
        reset: Date.now() + 60000,
        success: false,
      });

      // Need Redis available for rate limiting to work
      MOCK_GET_REDIS.mockReturnValue({} as never);

      const { POST } = await import("../search/route");
      const req = createMockNextRequest({
        body: { destination: "Paris" },
        method: "POST",
        url: "http://localhost/api/activities/search",
      });

      const res = await POST(req, createRouteParamsContext({}));

      expect(res.status).toBe(429);
      expect(LIMIT_SPY).toHaveBeenCalled();
    });
  });

  describe("GET /api/activities/[id]", () => {
    it("should return activity details", async () => {
      const mockActivity = {
        date: "2025-01-01",
        description: "Test",
        duration: 120,
        id: "places/123",
        location: "Test Location",
        name: "Test Activity",
        price: 2,
        rating: 4.5,
        type: "museum",
      };

      MOCK_SERVICE.details.mockResolvedValue(mockActivity);

      const { GET } = await import("../[id]/route");
      const req = createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/activities/places/123",
      });

      const routeContext = createRouteParamsContext({ id: "places/123" });

      const res = await GET(req, routeContext);
      const body = await res.json();

      expect(res.status).toBe(200);
      expect(body.id).toBe("places/123");
      expect(body.name).toBe("Test Activity");
      expect(MOCK_SERVICE.details).toHaveBeenCalledWith(
        "places/123",
        expect.objectContaining({ userId: expect.any(String) })
      );
    });

    it("should return 400 for missing place ID", async () => {
      const { GET } = await import("../[id]/route");
      const req = createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/activities/",
      });

      const routeContext = createRouteParamsContext({});

      const res = await GET(req, routeContext);
      const body = await res.json();

      expect(res.status).toBe(400);
      expect(body.error).toBe("invalid_request");
    });

    it("should return 404 when activity not found", async () => {
      MOCK_SERVICE.details.mockRejectedValue(
        new Error("Activity not found for Place ID: invalid")
      );

      const { GET } = await import("../[id]/route");
      const req = createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/activities/invalid",
      });

      const routeContext = createRouteParamsContext({ id: "invalid" });

      const res = await GET(req, routeContext);
      const body = await res.json();

      expect(res.status).toBe(404);
      expect(body.error).toBe("not_found");
    });

    it("should validate place ID format", async () => {
      const { GET } = await import("../[id]/route");
      const req = createMockNextRequest({
        method: "GET",
        url: "http://localhost/api/activities/",
      });

      const routeContext = createRouteParamsContext({ id: "" });

      const res = await GET(req, routeContext);
      const body = await res.json();

      expect(res.status).toBe(400);
      expect(body.error).toBe("invalid_request");
    });
  });
});
