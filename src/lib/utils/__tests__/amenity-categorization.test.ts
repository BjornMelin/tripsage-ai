import { describe, expect, it } from "vitest";

import { categorizeAmenities } from "@/lib/utils/amenity-categorization";

describe("categorizeAmenities", () => {
  it("buckets amenities by keyword", () => {
    const { essential, premium, unique, normalizedString } = categorizeAmenities([
      "Free WiFi",
      "Indoor Pool",
      "Rooftop Bar",
      "Breakfast Included",
      "Parking Garage",
    ]);

    expect(essential).toEqual(["Free WiFi", "Breakfast Included", "Parking Garage"]);
    expect(premium).toEqual(["Indoor Pool"]);
    expect(unique).toEqual(["Rooftop Bar"]);
    expect(normalizedString).toBe(
      "free wifi indoor pool rooftop bar breakfast included parking garage"
    );
  });

  it("handles empty amenities", () => {
    const { essential, premium, unique, normalizedString } = categorizeAmenities([]);

    expect(essential).toHaveLength(0);
    expect(premium).toHaveLength(0);
    expect(unique).toHaveLength(0);
    expect(normalizedString).toBe("");
  });

  it("handles null input gracefully", () => {
    const { essential, premium, unique } = categorizeAmenities(null);

    expect(essential).toEqual([]);
    expect(premium).toEqual([]);
    expect(unique).toEqual([]);
  });

  it("handles undefined input gracefully", () => {
    const { essential, premium, unique } = categorizeAmenities(undefined);

    expect(essential).toEqual([]);
    expect(premium).toEqual([]);
    expect(unique).toEqual([]);
  });

  it("matches keywords case-insensitively", () => {
    const { essential, premium, unique } = categorizeAmenities([
      "WIFI",
      "wifi",
      "Wifi",
      "WiFi",
      "PoOL",
      "POOL",
      "pool",
    ]);

    expect(essential).toEqual(["WIFI", "wifi", "Wifi", "WiFi"]);
    expect(premium).toEqual(["PoOL", "POOL", "pool"]);
    expect(unique).toHaveLength(0);
  });

  it("trims whitespace from amenities", () => {
    const { essential, premium, unique } = categorizeAmenities([
      "  WiFi  ",
      "\tBreakfast\n",
      "  Indoor Pool  ",
      "   ",
    ]);

    expect(essential).toEqual(["  WiFi  ", "\tBreakfast\n"]);
    expect(premium).toEqual(["  Indoor Pool  "]);
    expect(unique).toEqual(["   "]);
  });

  it("enforces precedence when amenity matches multiple categories", () => {
    // Test with an amenity that contains both essential and premium keywords
    // "Free WiFi and Pool" contains both "wifi" (essential) and "pool" (premium)
    // Precedence is essential > premium > unique, so it should go to essential
    const { essential, premium, unique } = categorizeAmenities([
      "Free WiFi and Pool Access", // Contains both "wifi" and "pool"
      "Fitness Center", // Contains "fitness" (premium)
      "Business Center", // No essential/premium keywords (unique)
    ]);

    // The multi-keyword amenity should appear in essential (highest precedence)
    expect(essential).toContain("Free WiFi and Pool Access");
    expect(essential).toHaveLength(1);

    // Fitness Center should be in premium
    expect(premium).toContain("Fitness Center");
    expect(premium).toHaveLength(1);

    // Business Center should be in unique
    expect(unique).toContain("Business Center");
    expect(unique).toHaveLength(1);

    // Each amenity should appear in only one category (no duplicates)
    const allClassified = [...essential, ...premium, ...unique];
    expect(allClassified).toHaveLength(3);
    expect(new Set(allClassified).size).toBe(3);

    // Verify no duplicates across categories
    const essentialSet = new Set(essential);
    const premiumSet = new Set(premium);
    const uniqueSet = new Set(unique);

    for (const item of essential) {
      expect(premiumSet.has(item)).toBe(false);
      expect(uniqueSet.has(item)).toBe(false);
    }
    for (const item of premium) {
      expect(essentialSet.has(item)).toBe(false);
      expect(uniqueSet.has(item)).toBe(false);
    }
  });

  it("correctly handles amenities with no keyword matches", () => {
    const { essential, premium, unique } = categorizeAmenities([
      "Ocean View",
      "Historic Building",
      "Pet Friendly",
      "Balcony",
    ]);

    // All amenities lack essential and premium keywords
    expect(essential).toHaveLength(0);
    expect(premium).toHaveLength(0);
    expect(unique).toEqual([
      "Ocean View",
      "Historic Building",
      "Pet Friendly",
      "Balcony",
    ]);
  });

  it("uses word boundaries to prevent false positives", () => {
    const { essential, premium, unique } = categorizeAmenities([
      "WiFi Access",
      "Free WiFi",
      "Wireless Internet",
      "WiFi Hotspot",
      "Swimming Pool",
      "Pool Lounge",
      "Poolside Bar", // "poolside" is a different word, won't match "pool" keyword
    ]);

    // Word boundary matching: "wifi" matches "WiFi", "Pool Lounge" matches "pool"
    // But "Poolside Bar" doesn't match "pool" because "poolside" is a different word
    expect(essential).toEqual(["WiFi Access", "Free WiFi", "WiFi Hotspot"]);
    expect(premium).toEqual(["Swimming Pool", "Pool Lounge"]);
    expect(unique).toEqual(["Wireless Internet", "Poolside Bar"]);
  });

  it("handles special characters and punctuation", () => {
    const { essential, premium, unique } = categorizeAmenities([
      "WiFi (Free)",
      "A/C Unit",
      "Breakfast - Complimentary",
      "Air Conditioning System",
    ]);

    expect(essential).toContain("WiFi (Free)");
    expect(essential).toContain("A/C Unit");
    expect(essential).toContain("Breakfast - Complimentary");
    expect(essential).toContain("Air Conditioning System");
    expect(premium).toHaveLength(0);
    expect(unique).toHaveLength(0);
  });
});
