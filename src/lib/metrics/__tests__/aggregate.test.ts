/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock dependencies before imports
const mockRedisGet = vi.fn();
const mockRedisSet = vi.fn();
const mockRedisDel = vi.fn();

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => ({
    del: mockRedisDel,
    get: mockRedisGet,
    set: mockRedisSet,
  })),
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    (
      _name: string,
      _opts: unknown,
      fn: (span: { setAttribute: ReturnType<typeof vi.fn> }) => Promise<unknown>
    ) => {
      const mockSpan = { setAttribute: vi.fn() };
      return Promise.resolve().then(() => fn(mockSpan));
    }
  ),
}));

describe("aggregate", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockRedisGet.mockResolvedValue(null);
    mockRedisSet.mockResolvedValue("OK");
    mockRedisDel.mockResolvedValue(1);
  });

  describe("windowToHours", () => {
    it("converts time windows correctly", async () => {
      const { windowToHours } = await import("@schemas/dashboard");

      expect(windowToHours("24h")).toBe(24);
      expect(windowToHours("7d")).toBe(168);
      expect(windowToHours("30d")).toBe(720);
      expect(windowToHours("all")).toBe(0);
    });
  });

  describe("aggregateDashboardMetrics", () => {
    it("returns cached data when available", async () => {
      const cachedData = {
        activeTrips: 5,
        avgLatencyMs: 123.45,
        completedTrips: 10,
        errorRate: 2.5,
        totalRequests: 1000,
        totalTrips: 15,
      };
      mockRedisGet.mockResolvedValue(cachedData);

      const { aggregateDashboardMetrics } = await import("../aggregate");

      const result = await aggregateDashboardMetrics(24);

      expect(result).toEqual(cachedData);
      expect(mockRedisGet).toHaveBeenCalledWith("dashboard:metrics:24h");
    });

    it("queries Supabase and caches result on cache miss", async () => {
      const { createServerSupabase } = await import("@/lib/supabase/server");

      const mockTrips = [
        { status: "completed" },
        { status: "completed" },
        { status: "planning" },
        { status: "booked" },
        { status: "cancelled" },
      ];

      const mockSelect = vi.fn().mockResolvedValue({
        data: mockTrips,
        error: null,
      });

      (createServerSupabase as ReturnType<typeof vi.fn>).mockResolvedValue({
        from: vi.fn().mockReturnValue({ select: mockSelect }),
      });

      const { aggregateDashboardMetrics } = await import("../aggregate");

      const result = await aggregateDashboardMetrics(24);

      expect(result.totalTrips).toBe(5);
      expect(result.completedTrips).toBe(2);
      expect(result.activeTrips).toBe(2);
      expect(mockRedisSet).toHaveBeenCalledWith(
        "dashboard:metrics:24h",
        expect.any(Object),
        { ex: 300 }
      );
    });

    it("handles missing trips gracefully", async () => {
      const { createServerSupabase } = await import("@/lib/supabase/server");

      const mockSelect = vi.fn().mockResolvedValue({
        data: null,
        error: null,
      });

      (createServerSupabase as ReturnType<typeof vi.fn>).mockResolvedValue({
        from: vi.fn().mockReturnValue({ select: mockSelect }),
      });

      const { aggregateDashboardMetrics } = await import("../aggregate");

      const result = await aggregateDashboardMetrics(24);

      expect(result.totalTrips).toBe(0);
      expect(result.completedTrips).toBe(0);
      expect(result.activeTrips).toBe(0);
    });

    it("calculates metrics correctly with api_metrics data", async () => {
      const { createServerSupabase } = await import("@/lib/supabase/server");

      // Reset redis mock to not return cached
      mockRedisGet.mockResolvedValue(null);

      const mockSelect = vi.fn();
      const mockGte = vi.fn().mockReturnValue({
        limit: vi.fn().mockResolvedValue({
          data: [
            { duration_ms: 100, status_code: 200 },
            { duration_ms: 200, status_code: 200 },
            { duration_ms: 150, status_code: 500 },
            { duration_ms: 250, status_code: 400 },
          ],
          error: null,
        }),
      });

      // First call for trips, second for api_metrics
      mockSelect
        .mockResolvedValueOnce({ data: [], error: null }) // trips
        .mockReturnValueOnce({ gte: mockGte }); // api_metrics

      (createServerSupabase as ReturnType<typeof vi.fn>).mockResolvedValue({
        from: vi.fn().mockReturnValue({ select: mockSelect }),
      });

      const { aggregateDashboardMetrics } = await import("../aggregate");

      const result = await aggregateDashboardMetrics(24);

      expect(result.totalRequests).toBe(4);
      // (100 + 200 + 150 + 250) / 4 = 175
      expect(result.avgLatencyMs).toBe(175);
      // 2 errors out of 4 = 50%
      expect(result.errorRate).toBe(50);
    });
  });

  describe("invalidateDashboardCache", () => {
    it("invalidates specific window cache", async () => {
      const { invalidateDashboardCache } = await import("../aggregate");

      await invalidateDashboardCache(24);

      expect(mockRedisDel).toHaveBeenCalledWith("dashboard:metrics:24h");
    });

    it("invalidates all window caches when no window specified", async () => {
      const { invalidateDashboardCache } = await import("../aggregate");

      await invalidateDashboardCache();

      expect(mockRedisDel).toHaveBeenCalledWith("dashboard:metrics:24h");
      expect(mockRedisDel).toHaveBeenCalledWith("dashboard:metrics:168h");
      expect(mockRedisDel).toHaveBeenCalledWith("dashboard:metrics:720h");
      expect(mockRedisDel).toHaveBeenCalledWith("dashboard:metrics:0h");
    });
  });

  describe("dashboardMetricsSchema", () => {
    it("validates correct metrics", async () => {
      const { dashboardMetricsSchema } = await import("@schemas/dashboard");

      const validMetrics = {
        activeTrips: 5,
        avgLatencyMs: 123.45,
        completedTrips: 10,
        errorRate: 2.5,
        totalRequests: 1000,
        totalTrips: 15,
      };

      const result = dashboardMetricsSchema.safeParse(validMetrics);
      expect(result.success).toBe(true);
    });

    it("rejects invalid metrics", async () => {
      const { dashboardMetricsSchema } = await import("@schemas/dashboard");

      const invalidMetrics = {
        activeTrips: -1, // negative not allowed
        avgLatencyMs: 123.45,
        completedTrips: 10,
        errorRate: 150, // > 100 not allowed
        totalRequests: 1000,
        totalTrips: 15,
      };

      const result = dashboardMetricsSchema.safeParse(invalidMetrics);
      expect(result.success).toBe(false);
    });

    it("rejects extra properties (strict)", async () => {
      const { dashboardMetricsSchema } = await import("@schemas/dashboard");

      const withExtra = {
        activeTrips: 5,
        avgLatencyMs: 123.45,
        completedTrips: 10,
        errorRate: 2.5,
        extraField: "not allowed",
        totalRequests: 1000,
        totalTrips: 15,
      };

      const result = dashboardMetricsSchema.safeParse(withExtra);
      expect(result.success).toBe(false);
    });
  });

  describe("timeWindowSchema", () => {
    it("validates allowed windows", async () => {
      const { timeWindowSchema } = await import("@schemas/dashboard");

      expect(timeWindowSchema.safeParse("24h").success).toBe(true);
      expect(timeWindowSchema.safeParse("7d").success).toBe(true);
      expect(timeWindowSchema.safeParse("30d").success).toBe(true);
      expect(timeWindowSchema.safeParse("all").success).toBe(true);
    });

    it("rejects invalid windows", async () => {
      const { timeWindowSchema } = await import("@schemas/dashboard");

      expect(timeWindowSchema.safeParse("1h").success).toBe(false);
      expect(timeWindowSchema.safeParse("invalid").success).toBe(false);
    });
  });
});
