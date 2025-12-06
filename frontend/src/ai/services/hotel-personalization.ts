/**
 * @fileoverview AI-powered hotel personalization service.
 *
 * Uses generateObject to produce personalized recommendations:
 * - Personalized tags based on user preferences
 * - Recommendation reason explaining the match
 * - Recommendation score (1-10)
 * - Vibe classification (luxury, business, family, romantic, adventure)
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import { generateObject } from "ai";
import { z } from "zod";
import { hashInputForCache } from "@/lib/cache/hash";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { sanitizeArray, sanitizeForPrompt } from "@/lib/security/prompt-sanitizer";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Cache TTL for personalization results (30 minutes). */
const PERSONALIZATION_CACHE_TTL = 1800;

/** Hotel vibe classification */
export type HotelVibe = "luxury" | "business" | "family" | "romantic" | "adventure";

/** User preference context for personalization */
export interface UserPreferences {
  /** User's travel style (e.g., "budget", "luxury", "adventure") */
  travelStyle?: string;
  /** Preferred amenities */
  preferredAmenities?: string[];
  /** Purpose of travel */
  tripPurpose?: string;
  /** Whether traveling with family */
  withFamily?: boolean;
  /** Whether traveling for business */
  forBusiness?: boolean;
}

/** Hotel data for personalization */
export interface HotelForPersonalization {
  /** Hotel name */
  name: string;
  /** Brand (e.g., "Marriott", "Hilton") */
  brand?: string;
  /** Star rating (1-5) */
  starRating?: number;
  /** Available amenities */
  amenities: string[];
  /** Property category */
  category?: string;
  /** Location description */
  location: string;
  /** Price per night */
  pricePerNight: number;
  /** User rating */
  rating?: number;
}

/** Personalization result for a single hotel */
export interface HotelPersonalization {
  /** Personalized tags for the user (max 3) */
  personalizedTags: string[];
  /** Why this hotel is recommended for the user */
  reason: string;
  /** Recommendation score (1-10) */
  score: number;
  /** Hotel vibe classification */
  vibe: HotelVibe;
}

/** Indexed personalization for caching (preserves hotel index) */
interface IndexedPersonalization extends HotelPersonalization {
  /** Original hotel index from AI response */
  index: number;
}

/** Schema for batch personalization response */
const personalizationResponseSchema = z.object({
  hotels: z.array(
    z.object({
      /** Hotel index in the input array */
      index: z.number().int().nonnegative(),
      /** Personalized tags (max 3) */
      personalizedTags: z.array(z.string()).max(3),
      /** Recommendation reason */
      reason: z.string(),
      /** Recommendation score 1-10 */
      score: z.number().int().min(1).max(10),
      /** Vibe classification */
      vibe: z.enum(["luxury", "business", "family", "romantic", "adventure"]),
    })
  ),
});

/**
 * Build cache key for personalization request.
 * Uses sorted copy of hotel identifiers to ensure deterministic cache keys.
 */
function buildPersonalizationCacheKey(
  userId: string,
  hotelIds: string[],
  preferences: UserPreferences
): string {
  // Sort a copy to avoid mutating the input array
  const sortedIds = [...hotelIds].sort();
  const input = JSON.stringify({ hotelIds: sortedIds, preferences });
  const hash = hashInputForCache(input);
  return `hotel:personalize:${userId}:${hash}`;
}

/**
 * Build prompt for hotel personalization.
 * All user inputs are sanitized to prevent prompt injection.
 */
function buildPersonalizationPrompt(
  hotels: HotelForPersonalization[],
  preferences: UserPreferences
): string {
  const hotelDescriptions = hotels
    .map((h, i) => {
      const safeName = sanitizeForPrompt(h.name, 100);
      const safeBrand = h.brand ? sanitizeForPrompt(h.brand, 50) : "Independent";
      const safeLocation = sanitizeForPrompt(h.location, 100);
      const safeCategory = h.category ? sanitizeForPrompt(h.category, 30) : "hotel";
      const safeAmenities = sanitizeArray(h.amenities, 10, 30).join(", ");
      return `[${i}] "${safeName}" (${safeBrand}, ${h.starRating ?? "?"}★, $${h.pricePerNight}/night, ${safeCategory}) at "${safeLocation}". Amenities: "${safeAmenities || "N/A"}".`;
    })
    .join("\n");

  const prefParts: string[] = [];
  if (preferences.travelStyle) {
    prefParts.push(`Travel style: ${sanitizeForPrompt(preferences.travelStyle, 50)}`);
  }
  if (preferences.tripPurpose) {
    prefParts.push(`Trip purpose: ${sanitizeForPrompt(preferences.tripPurpose, 50)}`);
  }
  if (preferences.withFamily) {
    prefParts.push("Traveling with family");
  }
  if (preferences.forBusiness) {
    prefParts.push("Business travel");
  }
  if (preferences.preferredAmenities?.length) {
    const safeAmenities = sanitizeArray(preferences.preferredAmenities, 10, 30).join(", ");
    prefParts.push(`Preferred amenities: ${safeAmenities}`);
  }

  const preferencesText = prefParts.length
    ? prefParts.join(". ")
    : "No specific preferences provided.";

  return `You are a hotel recommendation assistant. Analyze hotels and provide personalized recommendations strictly following the output schema.

USER PREFERENCES:
${preferencesText}

HOTELS:
${hotelDescriptions}

For each hotel, provide:
1. personalizedTags: Up to 3 short tags highlighting why this hotel suits this traveler (e.g., "Great for remote work", "Family pool", "Near attractions")
2. reason: A brief sentence explaining why this hotel is a good/poor match for the user
3. score: 1-10 recommendation score based on preference match (10 = perfect match)
4. vibe: Classify the hotel as one of: luxury, business, family, romantic, adventure

Return results for all ${hotels.length} hotels in index order.`;
}

/**
 * Personalize hotels for a user using AI.
 *
 * Analyzes hotels against user preferences to generate:
 * - Personalized tags
 * - Match explanations
 * - Recommendation scores
 * - Vibe classifications
 *
 * Results are cached per-user for 30 minutes.
 *
 * @param userId - User ID for caching and provider resolution
 * @param hotels - Hotels to personalize
 * @param preferences - User travel preferences
 * @returns Map of hotel index to personalization result
 */
export async function personalizeHotels(
  userId: string,
  hotels: HotelForPersonalization[],
  preferences: UserPreferences
): Promise<Map<number, HotelPersonalization>> {
  return await withTelemetrySpan(
    "ai.hotel.personalize",
    {
      attributes: { hotelCount: hotels.length, userId },
      redactKeys: ["userId"],
    },
    async () => {
      // Skip if no hotels
      if (hotels.length === 0) {
        return new Map();
      }

      // Check cache - use name+location for unique identification
      const hotelIds = hotels.map((h) => `${h.name}|${h.location.slice(0, 50)}`);
      const cacheKey = buildPersonalizationCacheKey(userId, hotelIds, preferences);
      const cached = await getCachedJson<IndexedPersonalization[]>(cacheKey);

      if (cached) {
        const result = new Map<number, HotelPersonalization>();
        for (const indexed of cached) {
          const { index, ...personalization } = indexed;
          result.set(index, personalization);
        }
        return result;
      }

      // Generate via AI
      const prompt = buildPersonalizationPrompt(hotels, preferences);
      const { model } = await resolveProvider(userId, "gpt-4o-mini");

      const response = await generateObject({
        model,
        prompt,
        schema: personalizationResponseSchema,
      });

      // Build result map and indexed cache array
      const result = new Map<number, HotelPersonalization>();
      const indexedPersonalizations: IndexedPersonalization[] = [];

      for (const hotel of response.object?.hotels ?? []) {
        const personalization: HotelPersonalization = {
          personalizedTags: hotel.personalizedTags,
          reason: hotel.reason,
          score: hotel.score,
          vibe: hotel.vibe,
        };
        result.set(hotel.index, personalization);
        // Store with index for correct cache reconstruction
        indexedPersonalizations.push({ ...personalization, index: hotel.index });
      }

      // Cache indexed results to preserve hotel indices
      await setCachedJson(cacheKey, indexedPersonalizations, PERSONALIZATION_CACHE_TTL);

      return result;
    }
  );
}

/**
 * Get default personalization for a hotel when AI is unavailable.
 *
 * Uses heuristics based on hotel data to provide basic personalization.
 *
 * @param hotel - Hotel to personalize
 * @returns Default personalization result
 */
export function getDefaultPersonalization(
  hotel: HotelForPersonalization
): HotelPersonalization {
  // Determine vibe from category and amenities
  let vibe: HotelVibe = "business";
  const amenitiesLower = hotel.amenities.map((a) => a.toLowerCase()).join(" ");
  const categoryLower = (hotel.category ?? "").toLowerCase();

  if (categoryLower.includes("resort") || amenitiesLower.includes("spa")) {
    vibe = "luxury";
  } else if (
    amenitiesLower.includes("kid") ||
    amenitiesLower.includes("family") ||
    amenitiesLower.includes("playground")
  ) {
    vibe = "family";
  } else if (
    amenitiesLower.includes("romantic") ||
    categoryLower.includes("boutique")
  ) {
    vibe = "romantic";
  } else if (amenitiesLower.includes("hiking") || amenitiesLower.includes("outdoor")) {
    vibe = "adventure";
  }

  // Generate basic tags
  const tags: string[] = [];
  if (hotel.rating && hotel.rating >= 4.5) {
    tags.push("Highly rated");
  }
  if (hotel.starRating && hotel.starRating >= 4) {
    tags.push(`${hotel.starRating}-star property`);
  }
  if (hotel.pricePerNight < 150) {
    tags.push("Great value");
  }

  // Default score based on rating
  const score = Math.min(10, Math.max(1, Math.round((hotel.rating ?? 3) * 2)));

  return {
    personalizedTags: tags.slice(0, 3),
    reason: `${hotel.name} is a ${vibe} option in ${hotel.location}.`,
    score,
    vibe,
  };
}
