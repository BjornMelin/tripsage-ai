/** @vitest-environment node */

import { StateDepartmentProvider } from "@ai/tools/server/travel-advisory/providers/state-department";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { server } from "@/test/msw/server";

const TRAVEL_ADVISORIES_URL = "https://cadataapi.state.gov/api/TravelAdvisories";

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

afterEach(() => server.resetHandlers());

describe("StateDepartmentProvider", () => {
  let provider: StateDepartmentProvider;

  beforeEach(() => {
    provider = new StateDepartmentProvider();
    server.use(
      http.get(TRAVEL_ADVISORIES_URL, () => HttpResponse.json(mockAdvisoryResponse))
    );
  });

  describe("getProviderName", () => {
    test("returns correct provider name", () => {
      expect(provider.getProviderName()).toBe("state_department");
    });
  });

  describe("getCountryAdvisory", () => {
    test("fetches and normalizes advisory for valid country code", async () => {
      const result = await provider.getCountryAdvisory("US");
      expect(result).not.toBeNull();
      expect(result?.destination).toBe("US");
      expect(result?.overallScore).toBe(85);
      expect(result?.provider).toBe("state_department");
      expect(result?.categories.length).toBeGreaterThan(0);
    });

    test("returns null for invalid country code", async () => {
      const result = await provider.getCountryAdvisory("XX");
      expect(result).toBeNull();
    });

    test("returns null for empty country code", async () => {
      const result = await provider.getCountryAdvisory("");
      expect(result).toBeNull();
    });

    test("handles API errors gracefully", async () => {
      server.use(http.get(TRAVEL_ADVISORIES_URL, () => HttpResponse.error()));
      const result = await provider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("handles non-OK API responses", async () => {
      server.use(
        http.get(TRAVEL_ADVISORIES_URL, () =>
          HttpResponse.json({ error: "fail" }, { status: 500 })
        )
      );
      const result = await provider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("handles invalid API response format", async () => {
      server.use(
        http.get(TRAVEL_ADVISORIES_URL, () => HttpResponse.json({ invalid: "format" }))
      );
      const result = await provider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("caches feed for subsequent requests", async () => {
      let requestCount = 0;

      server.use(
        http.get(TRAVEL_ADVISORIES_URL, () => {
          requestCount += 1;
          return HttpResponse.json(mockAdvisoryResponse);
        })
      );

      await provider.getCountryAdvisory("US");
      await provider.getCountryAdvisory("FR");
      expect(requestCount).toBe(1);
    });

    test("normalizes Level 2 advisory correctly", async () => {
      const result = await provider.getCountryAdvisory("FR");
      expect(result).not.toBeNull();
      expect(result?.overallScore).toBe(60);
      expect(result?.categories.length).toBeGreaterThan(0);
    });

    test("extracts categories from summary", async () => {
      const result = await provider.getCountryAdvisory("FR");
      expect((result?.categories.length ?? 0) > 0).toBe(true);
      const categoryNames =
        result?.categories.map((category) => category.category) ?? [];
      expect(categoryNames.some((name) => ["terrorism", "crime"].includes(name))).toBe(
        true
      );
    });

    test("uses stale cache when API fails", async () => {
      await provider.getCountryAdvisory("US");
      server.use(
        http.get("https://cadataapi.state.gov/api/TravelAdvisories", () =>
          HttpResponse.error()
        )
      );
      const result = await provider.getCountryAdvisory("US");
      expect(result).not.toBeNull();
    });

    test("finds advisory by direct category match", async () => {
      const advisoryWithDirectCode = [
        {
          Category: ["US"],
          id: "us-advisory",
          Link: "https://travel.state.gov/...",
          Published: "2024-01-01T00:00:00-05:00",
          Summary: "<p>Test advisory.</p>",
          Title: "United States - Level 1: Exercise Normal Precautions",
          Updated: "2024-01-01T00:00:00-05:00",
        },
      ];

      server.use(
        http.get(TRAVEL_ADVISORIES_URL, () => HttpResponse.json(advisoryWithDirectCode))
      );

      const result = await provider.getCountryAdvisory("US");
      expect(result).not.toBeNull();
      expect(result?.destination).toBe("US");
    });

    test("handles timeout errors without cache", async () => {
      server.use(
        http.get(TRAVEL_ADVISORIES_URL, () => HttpResponse.json({}, { status: 504 }))
      );

      const result = await provider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("handles timeout errors with stale cache", async () => {
      await provider.getCountryAdvisory("US");

      server.use(
        http.get(TRAVEL_ADVISORIES_URL, () => HttpResponse.json({}, { status: 504 }))
      );

      const result = await provider.getCountryAdvisory("US");
      expect(result).not.toBeNull();
    });

    test("handles malformed JSON response", async () => {
      server.use(http.get(TRAVEL_ADVISORIES_URL, () => HttpResponse.text("not-json")));

      const result = await provider.getCountryAdvisory("US");
      expect(result).toBeNull();
    });

    test("handles country code with length !== 2", async () => {
      expect(await provider.getCountryAdvisory("USA")).toBeNull();
      expect(await provider.getCountryAdvisory("U")).toBeNull();
      expect(await provider.getCountryAdvisory("")).toBeNull();
    });
  });
});
