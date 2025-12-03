/**
 * @fileoverview Client-safe formatting utilities for Google Places data.
 *
 * Provides formatting functions that can be used in both client and server components.
 */

/**
 * Format Google Places destination types into human-readable labels.
 *
 * Maps Google Places API type identifiers to user-friendly display names.
 * Returns up to 2 types joined with commas.
 *
 * @param types - Array of Google Places type identifiers (e.g., "locality", "country").
 * @returns Formatted string of destination types (e.g., "City, Country").
 */
export function formatDestinationTypes(types: string[]): string {
  const typeMap: Record<string, string> = {
    // biome-ignore lint/style/useNamingConvention: API values use snake_case
    administrative_area: "Region",
    country: "Country",
    establishment: "Landmark",
    locality: "City",
    natural_feature: "Natural Feature",
    political: "Administrative",
    tourist_attraction: "Attraction",
  };

  return types
    .map((type) => typeMap[type] || type.replace(/_/g, " "))
    .slice(0, 2)
    .join(", ");
}


