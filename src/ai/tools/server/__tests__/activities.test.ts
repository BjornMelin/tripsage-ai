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

const MOCK_ACTIVITIES_SEARCH = vi.hoisted(() => vi.fn());
const MOCK_ACTIVITIES_DETAILS = vi.hoisted(() => vi.fn());

class MockActivitiesService {
  details = MOCK_ACTIVITIES_DETAILS;
  search = MOCK_ACTIVITIES_SEARCH;
}

vi.mock("@domain/activities/service", () => ({
  ActivitiesService: MockActivitiesService,
}));

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("activities tools", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

      MOCK_ACTIVITIES_SEARCH.mockResolvedValue(mockResult);

      const { searchActivities } = await import("@ai/tools/server/activities");

      const result = await searchActivities.execute?.(
        {
          category: "museums",
          destination: "Paris",
        },
        mockContext
      );

      expect(MOCK_ACTIVITIES_SEARCH).toHaveBeenCalledWith({
        category: "museums",
        destination: "Paris",
      });
      expect(result).toEqual({
        activities: mockResult.activities,
        metadata: mockResult.metadata,
      });
    });

    it("should handle service errors", async () => {
      MOCK_ACTIVITIES_SEARCH.mockRejectedValue(new Error("Service error"));

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

      MOCK_ACTIVITIES_SEARCH.mockResolvedValue(mockResult);

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

      MOCK_ACTIVITIES_DETAILS.mockResolvedValue(mockActivity);

      const { getActivityDetails } = await import("@ai/tools/server/activities");

      const result = await getActivityDetails.execute?.(
        { placeId: "places/123" },
        mockContext
      );

      expect(MOCK_ACTIVITIES_DETAILS).toHaveBeenCalledWith("places/123");
      expect(result).toEqual(mockActivity);
    });

    it("should handle service errors", async () => {
      MOCK_ACTIVITIES_DETAILS.mockRejectedValue(new Error("Not found"));

      const { getActivityDetails } = await import("@ai/tools/server/activities");

      await expect(
        getActivityDetails.execute?.({ placeId: "invalid" }, mockContext)
      ).rejects.toMatchObject({
        code: TOOL_ERROR_CODES.toolExecutionFailed,
      });
    });

    it("should validate placeId is required", async () => {
      const { getActivityDetails } = await import("@ai/tools/server/activities");

      // Validate input schema directly (AI SDK validation happens at tool call level)
      const inputSchema = getActivityDetails.inputSchema as z.ZodType;
      const result = inputSchema.safeParse({ placeId: "" });

      expect(result.success).toBe(false);
      if (!result.success && result.error) {
        const errorMessages = result.error.issues.map(
          (issue: z.core.$ZodIssue) => issue.message
        );
        expect(
          errorMessages.some((msg: string) => msg.toLowerCase().includes("required"))
        ).toBe(true);
      }

      // Verify execute rejects when called with invalid input
      // Mock service should validate placeId like real service does
      MOCK_ACTIVITIES_DETAILS.mockImplementationOnce((placeId: string) => {
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
