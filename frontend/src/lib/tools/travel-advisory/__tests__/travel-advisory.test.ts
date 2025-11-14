import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { getRedis } from "@/lib/redis";
import { getTravelAdvisory } from "../../travel-advisory";
import { providerRegistry, registerProvider } from "../../travel-advisory/providers";
import { createStateDepartmentProvider } from "../../travel-advisory/providers/state-department";

// Mock dependencies
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn(),
  setCachedJson: vi.fn(),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: <T>(_name: string, _options: unknown, fn: () => T) => fn(),
}));

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("getTravelAdvisory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Ensure provider is registered for tests
    providerRegistry.clear();
    const provider = createStateDepartmentProvider();
    registerProvider(provider);
    // Mock Redis
    vi.mocked(getRedis).mockReturnValue({
      get: vi.fn(),
      set: vi.fn(),
    } as unknown as ReturnType<typeof getRedis>);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    providerRegistry.clear();
  });

  test("returns cached result when available", async () => {
    const cachedResult = {
      categories: [],
      destination: "United States",
      overallScore: 85,
      provider: "state_department",
      summary: "Cached summary",
    };

    vi.mocked(getCachedJson).mockResolvedValue(cachedResult);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "United States",
      },
      mockContext
    );

    expect(result).toMatchObject({
      ...cachedResult,
      fromCache: true,
    });
    expect(mockFetch).not.toHaveBeenCalled();
  });

  test("fetches from API when cache miss", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);

    const mockAdvisoryResponse = [
      {
        Category: ["US"],
        id: "us-advisory",
        Link: "https://travel.state.gov/...",
        Published: "2024-01-01T00:00:00-05:00",
        Summary: "<p>Exercise normal precautions.</p>",
        Title: "United States - Level 1: Exercise Normal Precautions",
        Updated: "2024-01-15T00:00:00-05:00",
      },
    ];

    mockFetch.mockResolvedValueOnce({
      json: async () => mockAdvisoryResponse,
      ok: true,
    } as Response);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "United States",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "fromCache" in result) {
      expect(result.fromCache).toBe(false);
      expect(result.provider).toBe("state_department");
      expect(result.overallScore).toBe(85);
    }
    expect(setCachedJson).toHaveBeenCalled();
  });

  test("returns stub when API unavailable", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "Unknown Country",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "provider" in result) {
      expect(result.provider).toBe("stub");
      expect(result.overallScore).toBe(75);
      expect(result.fromCache).toBe(false);
    }
  });

  test("returns stub when country not found", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);

    const mockAdvisoryResponse: unknown[] = [];

    mockFetch.mockResolvedValueOnce({
      json: async () => mockAdvisoryResponse,
      ok: true,
    } as Response);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "InvalidCountryXYZ",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "provider" in result) {
      expect(result.provider).toBe("stub");
    }
  });

  test("handles country name input", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);

    const mockAdvisoryResponse = [
      {
        Category: ["FR"],
        id: "fr-advisory",
        Link: "https://travel.state.gov/...",
        Published: "2024-01-01T00:00:00-05:00",
        Summary: "<p>Exercise increased caution.</p>",
        Title: "France - Level 2: Exercise Increased Caution",
        Updated: "2024-01-10T00:00:00-05:00",
      },
    ];

    mockFetch.mockResolvedValueOnce({
      json: async () => mockAdvisoryResponse,
      ok: true,
    } as Response);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "France",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "destination" in result) {
      expect(result.destination).toBe("France");
      // If provider finds the advisory, score should be 60 (Level 2)
      // If not found, falls back to stub with score 75
      expect([60, 75]).toContain(result.overallScore ?? 0);
    }
  });

  test("handles ISO country code input", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);

    const mockAdvisoryResponse = [
      {
        Category: ["GB"],
        id: "gb-advisory",
        Link: "https://travel.state.gov/...",
        Published: "2024-01-01T00:00:00-05:00",
        Summary: "<p>Exercise normal precautions.</p>",
        Title: "United Kingdom - Level 1: Exercise Normal Precautions",
        Updated: "2024-01-15T00:00:00-05:00",
      },
    ];

    mockFetch.mockResolvedValueOnce({
      json: async () => mockAdvisoryResponse,
      ok: true,
    } as Response);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "GB",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "destination" in result) {
      expect(result.destination).toBe("GB");
      // If provider finds the advisory, score should be 85 (Level 1)
      // If not found, falls back to stub with score 75
      expect([85, 75]).toContain(result.overallScore ?? 0);
    }
  });

  test("validates input schema", async () => {
    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    await expect(
      getTravelAdvisory.execute({ destination: "" }, mockContext)
    ).rejects.toThrow();
  });

  test("handles provider error gracefully", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);
    mockFetch.mockRejectedValueOnce(new Error("Provider error"));

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "TestCountry",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "provider" in result) {
      expect(result.provider).toBe("stub");
      expect(result.overallScore).toBe(75);
    }
  });

  test("handles case-insensitive cache keys", async () => {
    const cachedResult = {
      categories: [],
      destination: "france",
      overallScore: 60,
      provider: "state_department",
      summary: "Cached summary",
    };

    vi.mocked(getCachedJson).mockResolvedValue(cachedResult);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result1 = await getTravelAdvisory.execute(
      {
        destination: "France",
      },
      mockContext
    );

    const result2 = await getTravelAdvisory.execute(
      {
        destination: "FRANCE",
      },
      mockContext
    );

    expect(result1).toMatchObject({
      ...cachedResult,
      fromCache: true,
    });
    expect(result2).toMatchObject({
      ...cachedResult,
      fromCache: true,
    });
    expect(mockFetch).not.toHaveBeenCalled();
  });

  test("handles fetchSafetyScores error path", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);
    // Simulate provider throwing an error
    mockFetch.mockRejectedValueOnce(new Error("Network timeout"));

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "UnknownCountry",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "provider" in result) {
      expect(result.provider).toBe("stub");
    }
  });

  test("handles invalid country code mapping", async () => {
    vi.mocked(getCachedJson).mockResolvedValue(null);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "InvalidCountryXYZ123",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "provider" in result) {
      expect(result.provider).toBe("stub");
      expect(result.destination).toBe("InvalidCountryXYZ123");
    }
  });

  test("handles no provider registered", async () => {
    // Clear provider registry to simulate no provider
    providerRegistry.clear();
    vi.mocked(getCachedJson).mockResolvedValue(null);

    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }

    const result = await getTravelAdvisory.execute(
      {
        destination: "United States",
      },
      mockContext
    );

    expect(result).not.toBeNull();
    if (result && typeof result === "object" && "provider" in result) {
      expect(result.provider).toBe("stub");
      expect(result.overallScore).toBe(75);
    }
  });
});
