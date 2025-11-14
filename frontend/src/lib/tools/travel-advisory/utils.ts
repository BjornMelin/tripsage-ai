/**
 * @fileoverview Utility functions for travel advisory processing.
 *
 * Provides country code mapping, HTML parsing, and score conversion
 * utilities used by advisory providers.
 */

import { convert } from "html-to-text";
import countries from "i18n-iso-countries";

// Register English locale for country names
countries.registerLocale(require("i18n-iso-countries/langs/en.json"));

/**
 * Convert US State Department advisory level to safety score (0-100).
 *
 * Level 1: Exercise Normal Precautions → 85
 * Level 2: Exercise Increased Caution → 60
 * Level 3: Reconsider Travel → 35
 * Level 4: Do Not Travel → 10
 *
 * @param level - Advisory level (1-4).
 * @returns Safety score from 0-100.
 */
export function levelToScore(level: number): number {
  switch (level) {
    case 1:
      return 85;
    case 2:
      return 60;
    case 3:
      return 35;
    case 4:
      return 10;
    default:
      // Unknown level, return neutral score
      return 50;
  }
}

/**
 * Parse advisory level from State Department title string.
 *
 * Extracts level number from strings like "Austria - Level 1: Exercise Normal Precautions".
 *
 * @param title - Advisory title containing level information.
 * @returns Level number (1-4) or null if not found.
 */
export function parseAdvisoryLevel(title: string): number | null {
  const match = title.match(/Level\s+([1-4])/i);
  if (!match) {
    return null;
  }
  const level = Number.parseInt(match[1] ?? "0", 10);
  return level >= 1 && level <= 4 ? level : null;
}

/**
 * Convert HTML content to plain text.
 *
 * Strips HTML tags, preserves line breaks, and sanitizes content.
 *
 * @param html - HTML content to convert.
 * @returns Plain text with line breaks preserved.
 */
export function htmlToPlainText(html: string): string {
  return convert(html, {
    preserveNewlines: true,
    selectors: [
      { options: { ignoreHref: true }, selector: "a" },
      { format: "skip", selector: "img" },
      { format: "skip", selector: "script" },
      { format: "skip", selector: "style" },
    ],
    wordwrap: false,
  }).trim();
}

/**
 * Map country name or code to ISO-3166-1 alpha-2 code.
 *
 * Handles various formats:
 * - ISO codes: "US", "FR" → "US", "FR"
 * - Country names: "United States", "France" → "US", "FR"
 * - Category arrays: ["AU"] or ["Austria", "Europe"] → "AU"
 *
 * @param input - Country name, code, or category array.
 * @returns ISO-3166-1 alpha-2 code or null if not found.
 */
export function mapToCountryCode(input: string | string[]): string | null {
  if (Array.isArray(input)) {
    // Try each element in the array
    for (const item of input) {
      const code = mapToCountryCode(item);
      if (code) {
        return code;
      }
    }
    return null;
  }

  const normalized = input.trim().toUpperCase();

  // Check if already an ISO code (2 letters)
  if (normalized.length === 2 && /^[A-Z]{2}$/.test(normalized)) {
    if (countries.isValid(normalized)) {
      return normalized;
    }
  }

  // Try to find by country name
  const code = countries.getAlpha2Code(normalized, "en");
  if (code) {
    return code;
  }

  // Try fuzzy matching with common variations
  const variations: Record<string, string> = {
    "CZECH REPUBLIC": "CZ",
    "NORTH KOREA": "KP",
    // biome-ignore lint/style/useNamingConvention: Country name key
    RUSSIA: "RU",
    "SOUTH AFRICA": "ZA",
    "SOUTH KOREA": "KR",
    // biome-ignore lint/style/useNamingConvention: Common abbreviation
    UK: "GB",
    "UNITED KINGDOM": "GB",
    "UNITED STATES": "US",
    // biome-ignore lint/style/useNamingConvention: Common abbreviation
    USA: "US",
  };

  const upperInput = normalized.toUpperCase();
  if (upperInput in variations) {
    return variations[upperInput] ?? null;
  }

  return null;
}

/**
 * Extract safety categories from advisory summary.
 *
 * Parses HTML summary to identify mentioned risk categories
 * (crime, terrorism, health, civil unrest, etc.).
 *
 * @param summary - Plain text summary of advisory.
 * @returns Array of safety categories with descriptions.
 */
export function extractSafetyCategories(
  summary: string
): Array<{ category: string; value: number; description?: string }> {
  const categories: Array<{
    category: string;
    value: number;
    description?: string;
  }> = [];

  const lowerSummary = summary.toLowerCase();

  // Common risk categories and their keywords
  const riskKeywords: Record<string, { keywords: string[]; defaultScore: number }> = {
    "civil unrest": {
      defaultScore: 35,
      keywords: ["civil unrest", "demonstration", "protest", "riot"],
    },
    crime: {
      defaultScore: 40,
      keywords: ["crime", "theft", "robbery", "carjacking", "mugging"],
    },
    health: {
      defaultScore: 50,
      keywords: ["health", "medical", "disease", "outbreak", "vaccine"],
    },
    kidnapping: {
      defaultScore: 15,
      keywords: ["kidnapping", "abduction", "hostage"],
    },
    naturalDisaster: {
      defaultScore: 45,
      keywords: ["earthquake", "hurricane", "flood", "tsunami"],
    },
    terrorism: {
      defaultScore: 20,
      keywords: ["terrorism", "terrorist", "attack", "bombing"],
    },
  };

  for (const [category, { keywords, defaultScore }] of Object.entries(riskKeywords)) {
    const found = keywords.some((keyword) => lowerSummary.includes(keyword));
    if (found) {
      // Extract relevant sentence mentioning this category
      const sentences = summary.split(/[.!?]+/);
      const relevantSentence = sentences.find((s) =>
        keywords.some((k) => s.toLowerCase().includes(k))
      );

      // Map naturalDisaster back to natural_disaster for consistency
      const categoryName =
        category === "naturalDisaster" ? "natural_disaster" : category;
      categories.push({
        category: categoryName,
        description: relevantSentence?.trim(),
        value: defaultScore,
      });
    }
  }

  return categories;
}
