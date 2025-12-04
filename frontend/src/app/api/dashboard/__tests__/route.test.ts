/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/helpers/api-route";
import { createMockNextRequest } from "@/test/helpers/route";

/**
 * Dashboard route tests.
 *
 * Note: Full route integration tests require complex mocking of the
 * aggregateDashboardMetrics module chain. The core aggregation logic
 * is tested in src/lib/metrics/__tests__/aggregate.test.ts.
 *
 * These tests verify the route structure and authentication requirements.
 */
describe("/api/dashboard route", () => {
  beforeEach(() => {
    vi.resetModules();
    resetApiRouteMocks();
  });

  it("rejects unauthenticated requests with 401", async () => {
    mockApiRouteAuthUser(null);

    const mod = await import("../route");
    const req = createMockNextRequest({ url: "http://localhost/api/dashboard" });
    const res = await mod.GET(req, { params: Promise.resolve({}) });

    expect(res.status).toBe(401);
    const body = (await res.json()) as { error: string; reason: string };
    expect(body.error).toBe("unauthorized");
  });

  it("exports a GET handler function", async () => {
    const mod = await import("../route");
    expect(typeof mod.GET).toBe("function");
  });
});
