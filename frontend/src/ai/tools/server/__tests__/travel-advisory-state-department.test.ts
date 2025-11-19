import { StateDepartmentProvider } from "@ai/tools/server/travel-advisory/providers/state-department";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

// Mock fetch globally.
const mockFetch = vi.fn();
// biome-ignore lint/suspicious/noExplicitAny: Global assignment for test environment
(globalThis as any).fetch = mockFetch;

describe("StateDepartmentProvider", () => {
  let provider: StateDepartmentProvider;

  beforeEach(() => {
    provider = new StateDepartmentProvider();
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("getProviderName", () => {
    test("returns correct provider name", () => {
      expect(provider.getProviderName()).toBe("state_department");
    });
  });

  describe("getCountryAdvisory", () => {
    const mockAdvisoryResponse = [
      {
        Category: ["US"],
        id: "us-advisory",
        Link: "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/united-states-travel-advisory.html",
        Published: "2024-01-01T00:00:00-05:00",
        Summary:
          "<p>Exercise normal precautions in the United States.</p><p>Crime may occur in some areas.</p>",
        Title: "United States - Level 1: Exercise Normal Precautions",
        Updated: "2024-01-15T00:00:00-05:00",
      },
      {
        Category: ["FR"],
        id: "fr-advisory",
        Link: "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/france-travel-advisory.html",
        Published: "2024-01-01T00:00:00-05:00",
        Summary:
          "<p>Exercise increased caution due to <b>terrorism</b> and <b>crime</b>.</p>",
        Title: "France - Level 2: Exercise Increased Caution",
        Updated: "2024-01-10T00:00:00-05:00",
      },
    ];

    test("fetches and normalizes advisory for valid country code", async () => {
      mockFetch.mockResolvedValueOnce({
        json: async () => mockAdvisoryResponse,
        ok: true,
      } as Response);

      const result = await provider.getCountryAdvisory("US");

      expect(result).not.toBeNull();
      expect(result?.destination).toBe("US");
      expect(result?.overallScore).toBe(85);
      expect(result?.provider).toBe("state_department");
      expect(result?.sourceUrl).toBeTruthy();
      expect(result?.lastUpdated).toBeTruthy();
      expect(result?.summary).toBeTruthy();
      expect(result?.categories.length).toBeGreaterThan(0);
    });

    test("returns null for invalid country code", async () => {
      mockFetch.mockResolvedValueOnce({
        json: async () => mockAdvisoryResponse,
        ok: true,
      } as Response);

      const result = await provider.getCountryAdvisory("XX");

      expect(result).toBeNull();
    });

    test("returns null for empty country code", async () => {
      const result = await provider.getCountryAdvisory("");

      expect(result).toBeNull();
    });

    test("handles API errors gracefully", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await provider.getCountryAdvisory("US");

      expect(result).toBeNull();
    });

    test("handles non-OK API responses", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      } as Response);

      const result = await provider.getCountryAdvisory("US");

      expect(result).toBeNull();
    });

    test("handles invalid API response format", async () => {
      mockFetch.mockResolvedValueOnce({
        json: async () => ({ invalid: "format" }),
        ok: true,
      } as Response);

      const result = await provider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("caches feed for subsequent requests", async () => {
      mockFetch.mockResolvedValue({
        json: async () => mockAdvisoryResponse,
        ok: true,
      } as Response);

      await provider.getCountryAdvisory("US");
      expect(mockFetch).toHaveBeenCalledTimes(1);

      await provider.getCountryAdvisory("FR");
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    test("normalizes Level 2 advisory correctly", async () => {
      mockFetch.mockResolvedValueOnce({
        json: async () => mockAdvisoryResponse,
        ok: true,
      } as Response);

      const result = await provider.getCountryAdvisory("FR");

      expect(result).not.toBeNull();
      expect(result?.overallScore).toBe(60);
      expect(result?.categories.length).toBeGreaterThan(0);
    });

    test("extracts categories from summary", async () => {
      mockFetch.mockResolvedValueOnce({
        json: async () => mockAdvisoryResponse,
        ok: true,
      } as Response);

      const result = await provider.getCountryAdvisory("FR");

      expect(result?.categories.length).toBeGreaterThan(0);
      const categoryNames =
        result?.categories.map((category) => category.category) ?? [];
      expect(categoryNames.some((name) => ["terrorism", "crime"].includes(name))).toBe(
        true
      );
    });

    test("uses stale cache when API fails", async () => {
      const staleAdvisory = [
        {
          Category: ["US"],
          id: "us-advisory",
          Link: "https://travel.state.gov/...",
          Published: "2024-01-01T00:00:00-05:00",
          Summary: "<p>Stale data.</p>",
          Title: "United States - Level 1: Exercise Normal Precautions",
          Updated: "2024-01-01T00:00:00-05:00",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: async () => staleAdvisory,
        ok: true,
      } as Response);

      await provider.getCountryAdvisory("US");
      expect(mockFetch).toHaveBeenCalledTimes(1);

      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await provider.getCountryAdvisory("US");
      expect(result).not.toBeNull();
      expect(result?.destination).toBe("US");
    });

    test("finds advisory by direct category match", async () => {
      const freshProvider = new StateDepartmentProvider();
      const advisoryWithDirectCode = [
        {
          Category: ["US"],
          id: "us-advisory",
          Link: "https://travel.state.gov/...",
          Published: "2024-01-01T00:00:00-05:00",
          Summary: "<p>Test advisory.</p>",
          Title: "United States - Level 1: Exercise Normal Precautions",
          Updated: "2024-01-15T00:00:00-05:00",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: async () => advisoryWithDirectCode,
        ok: true,
      } as Response);

      const result = await freshProvider.getCountryAdvisory("US");
      expect(result).not.toBeNull();
      expect(result?.destination).toBe("US");
    });

    test("handles timeout errors without cache", async () => {
      const freshProvider = new StateDepartmentProvider();
      mockFetch.mockImplementationOnce(() =>
        Promise.reject(new DOMException("Timeout", "AbortError"))
      );

      const result = await freshProvider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("handles timeout errors with stale cache", async () => {
      const staleAdvisory = [
        {
          Category: ["US"],
          id: "us-advisory",
          Link: "https://travel.state.gov/...",
          Published: "2024-01-01T00:00:00-05:00",
          Summary: "<p>Stale data.</p>",
          Title: "United States - Level 1: Exercise Normal Precautions",
          Updated: "2024-01-01T00:00:00-05:00",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: async () => staleAdvisory,
        ok: true,
      } as Response);

      await provider.getCountryAdvisory("US");

      mockFetch.mockRejectedValueOnce(new DOMException("Timeout", "AbortError"));

      const result = await provider.getCountryAdvisory("US");
      expect(result).not.toBeNull();
      expect(result?.destination).toBe("US");
    });

    test("handles malformed JSON response", async () => {
      mockFetch.mockResolvedValueOnce({
        json: () => Promise.reject(new Error("Invalid JSON")),
        ok: true,
      } as unknown as Response);

      const result = await provider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("handles country code with length !== 2", async () => {
      mockFetch.mockResolvedValueOnce({
        json: async () => mockAdvisoryResponse,
        ok: true,
      } as Response);

      expect(await provider.getCountryAdvisory("USA")).toBeNull();
      expect(await provider.getCountryAdvisory("U")).toBeNull();
      expect(await provider.getCountryAdvisory("")).toBeNull();
    });
  });
});
