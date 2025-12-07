/**
 * Categorize amenities into essential, premium, and unique buckets.
 * Keeps logic reusable and testable across hotel personalization surfaces.
 */
export interface AmenityCategories {
  essential: string[];
  premium: string[];
  unique: string[];
  normalizedString: string;
}

const ESSENTIAL_KEYWORDS = [
  "wifi",
  "breakfast",
  "parking",
  "air conditioning",
  "air-conditioned",
  "a/c",
] as const;

const PREMIUM_KEYWORDS = ["spa", "pool", "gym", "fitness", "concierge"] as const;

export function categorizeAmenities(amenities?: string[] | null): AmenityCategories {
  // Guard against null/undefined input
  if (!Array.isArray(amenities) || amenities.length === 0) {
    return { essential: [], normalizedString: "", premium: [], unique: [] };
  }

  const normalized = amenities.map((amenity) => amenity.toLowerCase().trim());
  const normalizedString = normalized.join(" ");

  // Enforce precedence: essential > premium > unique
  const essential: string[] = [];
  const premium: string[] = [];
  const unique: string[] = [];

  // Single-pass classification with word boundary matching
  for (let idx = 0; idx < normalized.length; idx++) {
    const normalizedAmenity = normalized[idx];
    const originalAmenity = amenities[idx];
    if (!originalAmenity) continue;
    if (!normalizedAmenity) {
      // Empty after trimming (e.g., whitespace-only), add to unique
      unique.push(originalAmenity);
      continue;
    }

    let matched = false;

    // Check essential keywords with word boundaries
    for (const keyword of ESSENTIAL_KEYWORDS) {
      const regex = new RegExp(`\\b${keyword}\\b`, "i");
      if (regex.test(normalizedAmenity)) {
        essential.push(originalAmenity);
        matched = true;
        break;
      }
    }

    if (matched) continue;

    // Check premium keywords with word boundaries
    for (const keyword of PREMIUM_KEYWORDS) {
      const regex = new RegExp(`\\b${keyword}\\b`, "i");
      if (regex.test(normalizedAmenity)) {
        premium.push(originalAmenity);
        matched = true;
        break;
      }
    }

    if (matched) continue;

    // No keyword matched, add to unique
    unique.push(originalAmenity);
  }

  return { essential, normalizedString, premium, unique };
}
