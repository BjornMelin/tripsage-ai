/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock dependencies before imports
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
  incrCounter: vi.fn(),
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

describe("api-metrics", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  describe("recordApiMetric", () => {
    it("records metric to Supabase and increments Redis counters", async () => {
      const { getRedis, incrCounter } = await import("@/lib/redis");
      const { createServerSupabase } = await import("@/lib/supabase/server");

      const mockInsert = vi.fn().mockResolvedValue({ data: null, error: null });
      const mockFrom = vi.fn().mockReturnValue({ insert: mockInsert });
      (createServerSupabase as ReturnType<typeof vi.fn>).mockResolvedValue({
        from: mockFrom,
      });

      (getRedis as ReturnType<typeof vi.fn>).mockReturnValue({ mock: true });
      (incrCounter as ReturnType<typeof vi.fn>).mockResolvedValue(1);

      const { recordApiMetric } = await import("../api-metrics");

      await recordApiMetric({
        durationMs: 100,
        endpoint: "/api/test",
        method: "GET",
        statusCode: 200,
        userId: "user-123",
      });

      // Verify Supabase insert was called
      expect(mockFrom).toHaveBeenCalledWith("api_metrics");
      expect(mockInsert).toHaveBeenCalledWith(
        expect.objectContaining({
          duration_ms: 100,
          endpoint: "/api/test",
          method: "GET",
          status_code: 200,
          user_id: "user-123",
        })
      );

      // Verify Redis counters were incremented
      expect(incrCounter).toHaveBeenCalled();
    });

    it("handles missing Redis gracefully", async () => {
      const { getRedis } = await import("@/lib/redis");
      const { createServerSupabase } = await import("@/lib/supabase/server");

      (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(undefined);
      const mockInsert = vi.fn().mockResolvedValue({ data: null, error: null });
      (createServerSupabase as ReturnType<typeof vi.fn>).mockResolvedValue({
        from: vi.fn().mockReturnValue({ insert: mockInsert }),
      });

      const { recordApiMetric } = await import("../api-metrics");

      // Should not throw
      await expect(
        recordApiMetric({
          durationMs: 50,
          endpoint: "/api/test",
          method: "POST",
          statusCode: 201,
        })
      ).resolves.not.toThrow();
    });

    it("records error metrics with error type", async () => {
      const { getRedis, incrCounter } = await import("@/lib/redis");
      const { createServerSupabase } = await import("@/lib/supabase/server");

      const mockInsert = vi.fn().mockResolvedValue({ data: null, error: null });
      const mockFrom = vi.fn().mockReturnValue({ insert: mockInsert });
      (createServerSupabase as ReturnType<typeof vi.fn>).mockResolvedValue({
        from: mockFrom,
      });

      (getRedis as ReturnType<typeof vi.fn>).mockReturnValue({ mock: true });
      (incrCounter as ReturnType<typeof vi.fn>).mockResolvedValue(1);

      const { recordApiMetric } = await import("../api-metrics");

      await recordApiMetric({
        durationMs: 500,
        endpoint: "/api/error",
        errorType: "ValidationError",
        method: "POST",
        statusCode: 400,
      });

      expect(mockInsert).toHaveBeenCalledWith(
        expect.objectContaining({
          error_type: "ValidationError",
          status_code: 400,
        })
      );
    });
  });

  describe("fireAndForgetMetric", () => {
    it("does not throw on errors", async () => {
      const { createServerSupabase } = await import("@/lib/supabase/server");
      (createServerSupabase as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error("DB error")
      );

      const { fireAndForgetMetric } = await import("../api-metrics");

      // Should not throw
      expect(() =>
        fireAndForgetMetric({
          durationMs: 100,
          endpoint: "/api/test",
          method: "GET",
          statusCode: 200,
        })
      ).not.toThrow();
    });
  });
});
