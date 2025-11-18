/**
 * @fileoverview US State Department Travel Advisories API provider.
 *
 * Implements AdvisoryProvider for the US State Department's
 * official travel advisories API.
 */

import { createServerLogger } from "@/lib/telemetry/logger";
import type { AdvisoryProvider, SafetyResult } from "../providers";
import {
  extractSafetyCategories,
  htmlToPlainText,
  levelToScore,
  mapToCountryCode,
  parseAdvisoryLevel,
} from "../utils";

/**
 * State Department API advisory response structure.
 *
 * Note: Property names match the API response format (PascalCase).
 */
interface StateDepartmentAdvisory {
  // biome-ignore lint/style/useNamingConvention: API format
  Title: string;
  // biome-ignore lint/style/useNamingConvention: API format
  Link: string;
  // biome-ignore lint/style/useNamingConvention: API format
  Category: string[];
  // biome-ignore lint/style/useNamingConvention: API format
  Summary: string;
  id: string;
  // biome-ignore lint/style/useNamingConvention: API format
  Published: string;
  // biome-ignore lint/style/useNamingConvention: API format
  Updated: string;
}

/**
 * State Department Travel Advisories API provider.
 *
 * Fetches and normalizes travel advisory data from the US State
 * Department's official API.
 */
export class StateDepartmentProvider implements AdvisoryProvider {
  private readonly apiUrl = "https://cadataapi.state.gov/api/TravelAdvisories";
  private feedCache: StateDepartmentAdvisory[] | null = null;
  private feedCacheTimestamp: number = 0;
  private readonly feedCacheTtl = 24 * 60 * 60 * 1000; // 24 hours

  /**
   * Get provider name for attribution.
   *
   * @returns Provider identifier.
   */
  getProviderName(): string {
    return "state_department";
  }

  /**
   * Fetch and cache the full State Department advisories feed.
   *
   * @returns Promise resolving to array of advisories.
   * @throws Error if API request fails.
   */
  private async fetchFeed(): Promise<StateDepartmentAdvisory[]> {
    const now = Date.now();

    // Return cached feed if still valid
    if (this.feedCache && now - this.feedCacheTimestamp < this.feedCacheTtl) {
      return this.feedCache;
    }

    try {
      const response = await fetch(this.apiUrl, {
        headers: {
          // biome-ignore lint/style/useNamingConvention: HTTP header name
          Accept: "application/json",
        },
        // Add timeout to prevent hanging requests
        signal: AbortSignal.timeout(10000), // 10 seconds
      });

      if (!response.ok) {
        throw new Error(
          `State Department API returned ${response.status}: ${response.statusText}`
        );
      }

      const data = (await response.json()) as StateDepartmentAdvisory[];

      if (!Array.isArray(data)) {
        throw new Error("Invalid API response format: expected array");
      }

      // Cache the feed
      this.feedCache = data;
      this.feedCacheTimestamp = now;

      return data;
    } catch (error) {
      // If we have stale cache, return it
      if (this.feedCache) {
        return this.feedCache;
      }

      throw error;
    }
  }

  /**
   * Find advisory for a specific country code.
   *
   * @param feed - Full advisories feed.
   * @param countryCode - ISO-3166-1 alpha-2 country code.
   * @returns Matching advisory or null if not found.
   */
  private findAdvisoryByCountryCode(
    feed: StateDepartmentAdvisory[],
    countryCode: string
  ): StateDepartmentAdvisory | null {
    const upperCode = countryCode.toUpperCase();

    for (const advisory of feed) {
      // Check if Category array contains the country code
      const categoryCodes = advisory.Category.map((cat) =>
        mapToCountryCode(cat)
      ).filter((code): code is string => code !== null);

      if (categoryCodes.includes(upperCode)) {
        return advisory;
      }

      // Also check if any category string matches the code directly
      if (advisory.Category.some((cat) => cat.toUpperCase() === upperCode)) {
        return advisory;
      }
    }

    return null;
  }

  /**
   * Normalize State Department advisory to SafetyResult.
   *
   * Transforms raw API response (PascalCase) to normalized structure (camelCase),
   * extracts advisory level, parses HTML summary, and identifies safety categories.
   *
   * @param advisory - Raw advisory from API.
   * @param countryCode - ISO country code.
   * @returns Normalized safety result.
   */
  private normalizeAdvisory(
    advisory: StateDepartmentAdvisory,
    countryCode: string
  ): SafetyResult {
    const level = parseAdvisoryLevel(advisory.Title);
    const overallScore = level ? levelToScore(level) : 50;

    const summaryText = htmlToPlainText(advisory.Summary);
    const categories = extractSafetyCategories(summaryText);

    // If no categories extracted, create a default one from the level
    if (categories.length === 0 && level) {
      const levelDescriptions: Record<number, string> = {
        1: "Exercise Normal Precautions",
        2: "Exercise Increased Caution",
        3: "Reconsider Travel",
        4: "Do Not Travel",
      };
      categories.push({
        category: "overall_risk",
        description: levelDescriptions[level],
        value: overallScore,
      });
    }

    return {
      categories,
      destination: countryCode.toUpperCase(),
      lastUpdated: advisory.Updated,
      overallScore,
      provider: this.getProviderName(),
      sourceUrl: advisory.Link,
      summary: summaryText,
    };
  }

  /**
   * Get travel advisory for a country by ISO-3166-1 alpha-2 code.
   *
   * @param countryCode - Two-letter ISO country code (e.g., "US", "FR").
   * @returns Promise resolving to safety result or null if not found.
   */
  async getCountryAdvisory(countryCode: string): Promise<SafetyResult | null> {
    if (!countryCode || countryCode.length !== 2) {
      return null;
    }

    try {
      const feed = await this.fetchFeed();
      const advisory = this.findAdvisoryByCountryCode(feed, countryCode);

      if (!advisory) {
        return null;
      }

      return this.normalizeAdvisory(advisory, countryCode);
    } catch (error) {
      // Log error but don't throw - let caller handle fallback
      stateDepartmentLogger.error("api_request_failed", {
        countryCode,
        error: error instanceof Error ? error.message : "unknown_error",
      });
      return null;
    }
  }
}

/**
 * Create and register the State Department provider.
 *
 * @returns Provider instance.
 */
export function createStateDepartmentProvider(): AdvisoryProvider {
  const provider = new StateDepartmentProvider();
  return provider;
}

const stateDepartmentLogger = createServerLogger("tools.travel_advisory.state_dept");
