/** @vitest-environment node */

import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { z } from "zod";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

const TELEMETRY_SPAN = {
  addEvent: vi.fn(),
  setAttribute: vi.fn(),
};
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _opts, execute) => execute(TELEMETRY_SPAN)),
}));

vi.mock("@domain/activities/container", () => ({
  getActivitiesService: vi.fn(),
}));

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("activities tools", () => {
  let mockService: {
    search: ReturnType<typeof vi.fn>;
    details: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    mockService = {
      details: vi.fn(),
      search: vi.fn(),
    };

    const { getActivitiesService } = await import("@domain/activities/container");
    vi.mocked(getActivitiesService).mockReturnValue(mockService as never);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("searchActivities", () => {
    it("should call service.search and return formatted result", async () => {
      const mockResult = {
        activities: [
          {
            date: "2025-01-01",
            description: "Test description",
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

      mockService.search.mockResolvedValue(mockResult);

      const { searchActivities } = await import("@ai/tools/server/activities");

      const result = await searchActivities.execute?.(
        {
          category: "museums",
          destination: "Paris",
        },
        mockContext
      );

      expect(mockService.search).toHaveBeenCalledWith(
        { category: "museums", destination: "Paris" },
        {}
      );
      expect(result).toEqual({
        activities: mockResult.activities,
        metadata: mockResult.metadata,
      });
    });

    it("should handle service errors", async () => {
      mockService.search.mockRejectedValue(new Error("Service error"));

      const { searchActivities } = await import("@ai/tools/server/activities");

      await expect(
        searchActivities.execute?.({ destination: "Paris" }, mockContext)
      ).rejects.toMatchObject({
        code: TOOL_ERROR_CODES.toolExecutionFailed,
      });
    });

    it("should validate input schema", async () => {
      const { searchActivities } = await import("@ai/tools/server/activities");

      // Invalid input should be caught by Zod schema validation
      await expect(
        searchActivities.execute?.({ destination: "" }, mockContext)
      ).rejects.toThrow();
    });

    it("should include metadata notes when present", async () => {
      const mockResult = {
        activities: [],
        metadata: {
          cached: false,
          notes: ["Some results are AI suggestions"],
          primarySource: "ai_fallback" as const,
          sources: ["ai_fallback" as const],
          total: 0,
        },
      };

      mockService.search.mockResolvedValue(mockResult);

      const { searchActivities } = await import("@ai/tools/server/activities");

      const result = await searchActivities.execute?.(
        { destination: "Unknown" },
        mockContext
      );

      expect(result).toBeDefined();
      if (result && typeof result === "object" && "metadata" in result) {
        expect(result.metadata.notes).toEqual(["Some results are AI suggestions"]);
      }
    });
  });

  describe("getActivityDetails", () => {
    it("should call service.details and return activity", async () => {
      const mockActivity = {
        date: "2025-01-01",
        description: "Test description",
        duration: 120,
        id: "places/123",
        location: "Test Location",
        name: "Test Activity",
        price: 2,
        rating: 4.5,
        type: "museum",
      };

      mockService.details.mockResolvedValue(mockActivity);

      const { getActivityDetails } = await import("@ai/tools/server/activities");

      const result = await getActivityDetails.execute?.(
        { placeId: "places/123" },
        mockContext
      );

      expect(mockService.details).toHaveBeenCalledWith("places/123", {});
      expect(result).toEqual(mockActivity);
    });

    it("should handle service errors", async () => {
      mockService.details.mockRejectedValue(new Error("Not found"));

      const { getActivityDetails } = await import("@ai/tools/server/activities");

      await expect(
        getActivityDetails.execute?.({ placeId: "invalid" }, mockContext)
      ).rejects.toMatchObject({
        code: TOOL_ERROR_CODES.toolExecutionFailed,
      });
    });

    it("should validate placeId is required", async () => {
      const { getActivityDetails } = await import("@ai/tools/server/activities");
      const { z } = await import("zod");

      // Validate input schema directly (AI SDK validation happens at tool call level)
      const inputSchema = getActivityDetails.inputSchema as z.ZodSchema;
      const result = inputSchema.safeParse({ placeId: "" });

      expect(result.success).toBe(false);
      if (!result.success && result.error) {
        const errorMessages = result.error.issues.map((issue: z.core.$ZodIssue) => issue.message);
        expect(
          errorMessages.some((msg) => msg.toLowerCase().includes("required"))
        ).toBe(true);
      }

      // Verify execute rejects when called with invalid input
      // Mock service should validate placeId like real service does
      mockService.details.mockImplementationOnce((placeId: string) => {
        if (!placeId || placeId.trim().length === 0) {
          throw new Error("Place ID is required");
        }
        return Promise.resolve({} as never);
      });

      await expect(
        getActivityDetails.execute?.({ placeId: "" }, mockContext)
      ).rejects.toThrow("Place ID is required");
    });
  });
});
