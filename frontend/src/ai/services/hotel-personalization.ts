/**
 * @fileoverview AI-powered hotel personalization service.
 *
 * Uses AI SDK v6 structured output to produce personalized recommendations:
 * - Personalized tags based on user preferences
 * - Recommendation reason explaining the match
 * - Recommendation score (1-10)
 * - Vibe classification (luxury, business, family, romantic, adventure)
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import { generateText, Output } from "ai";
import { z } from "zod";
import { hashInputForCache } from "@/lib/cache/hash";
import { deleteCachedJson, getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { sanitizeArray, sanitizeForPrompt } from "@/lib/security/prompt-sanitizer";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";

/** Cache TTL for personalization results (30 minutes). */
export const PERSONALIZATION_CACHE_TTL = 1800;

const MAX_HOTELS_PER_REQUEST = 20;

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

/** Cached personalization keyed by stable hotel identifier */
interface IndexedPersonalization extends HotelPersonalization {
  /** Stable hotel identifier used for cache lookups */
  hotelId: string;
}

/** Schema for batch personalization response */
const personalizationResponseSchema = z.strictObject({
  hotels: z
    .array(
      z.strictObject({
        /** Hotel index in the input array */
        index: z
          .number()
          .int()
          .nonnegative({ error: "Index must be a non-negative integer" }),
        /** Personalized tags (max 3) */
        personalizedTags: z
          .array(z.string())
          .max(3, { error: "At most 3 tags allowed" }),
        /** Recommendation reason */
        reason: z.string(),
        /** Recommendation score 1-10 */
        score: z.number().int().min(1, { error: "Score must be at least 1" }).max(10, {
          error: "Score must be at most 10",
        }),
        /** Vibe classification */
        vibe: z.enum(["luxury", "business", "family", "romantic", "adventure"]),
      })
    )
    .max(MAX_HOTELS_PER_REQUEST, {
      error: `Cannot personalize more than ${MAX_HOTELS_PER_REQUEST} hotels`,
    }),
});

function buildHotelIdentifiers(hotels: HotelForPersonalization[]): string[] {
  return hotels.map((h) => {
    const locationHash = hashInputForCache({
      location: h.location,
      price: h.pricePerNight,
    });
    return `${h.name}|${locationHash}`;
  });
}

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
  const sortedPreferencesEntries = Object.entries(preferences).sort(([a], [b]) =>
    a.localeCompare(b)
  );
  const canonicalPreferences = Object.fromEntries(
    sortedPreferencesEntries.map(([key, value]) => {
      if (key === "preferredAmenities" && Array.isArray(value)) {
        return [key, [...value].sort()];
      }
      return [key, value];
    })
  );

  const input = JSON.stringify({
    hotelIds: sortedIds,
    preferences: canonicalPreferences,
  });
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
    const safeAmenities = sanitizeArray(preferences.preferredAmenities, 10, 30).join(
      ", "
    );
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

      if (hotels.length > MAX_HOTELS_PER_REQUEST) {
        throw new Error(
          `Cannot personalize more than ${MAX_HOTELS_PER_REQUEST} hotels per request`
        );
      }

      // Check cache - use stable hotel identifier to avoid order-dependent mismatches
      const hotelIds = buildHotelIdentifiers(hotels);
      const cacheKey = buildPersonalizationCacheKey(userId, hotelIds, preferences);
      const cached = await getCachedJson<IndexedPersonalization[]>(cacheKey);

      if (cached) {
        recordTelemetryEvent("cache.hotel_personalize", {
          attributes: { cache: "hotel.personalize", status: "hit" },
        });
        const result = new Map<number, HotelPersonalization>();
        const cachedByHotelId = new Map<string, HotelPersonalization>();
        for (const { hotelId, ...personalization } of cached) {
          cachedByHotelId.set(hotelId, personalization);
        }
        hotels.forEach((_hotel, index) => {
          const hotelId = hotelIds[index];
          const personalization = cachedByHotelId.get(hotelId);
          if (personalization) {
            result.set(index, personalization);
          } else {
            // Cache entry missing for this hotel; fall back to deterministic default
            result.set(index, getDefaultPersonalization(hotels[index]));
          }
        });
        return result;
      }

      recordTelemetryEvent("cache.hotel_personalize", {
        attributes: { cache: "hotel.personalize", status: "miss" },
      });

      // Generate via AI
      const prompt = buildPersonalizationPrompt(hotels, preferences);
      const { model } = await resolveProvider(userId, "gpt-4o-mini");

      let response: Awaited<ReturnType<typeof generateText>>;
      try {
        response = await generateText({
          model,
          output: Output.object({ schema: personalizationResponseSchema }),
          prompt,
        });
      } catch (error) {
        recordTelemetryEvent("ai.hotel.personalize.failure", {
          attributes: {
            cache: "hotel.personalize",
            error: error instanceof Error ? error.message : "unknown_error",
            status: "error",
          },
          level: "error",
        });
        const fallback = new Map<number, HotelPersonalization>();
        hotels.forEach((hotel, index) => {
          fallback.set(index, getDefaultPersonalization(hotel));
        });
        return fallback;
      }

      // Build result map and indexed cache array
      const result = new Map<number, HotelPersonalization>();
      const indexedPersonalizations: IndexedPersonalization[] = [];

      const hotelsResponse = response.output?.hotels ?? [];
      const seenIndices = new Set<number>();
      for (const hotel of hotelsResponse) {
        if (
          !Number.isInteger(hotel.index) ||
          hotel.index < 0 ||
          hotel.index >= hotels.length
        ) {
          recordTelemetryEvent("ai.hotel.personalize.invalid_index", {
            attributes: { hotelCount: hotels.length, index: hotel.index },
            level: "warning",
          });
          continue; // Skip invalid indices from AI
        }

        if (seenIndices.has(hotel.index)) {
          recordTelemetryEvent("ai.hotel.personalize.duplicate_index", {
            attributes: { hotelCount: hotels.length, index: hotel.index },
            level: "warning",
          });
          continue; // Skip duplicate indices to avoid overwriting earlier results
        }
        seenIndices.add(hotel.index);

        const personalization: HotelPersonalization = {
          personalizedTags: hotel.personalizedTags,
          reason: hotel.reason,
          score: hotel.score,
          vibe: hotel.vibe,
        };
        const hotelId = hotelIds[hotel.index];
        if (!hotelId) {
          recordTelemetryEvent("ai.hotel.personalize.missing_hotel_id", {
            attributes: { hotelCount: hotels.length, index: hotel.index },
            level: "warning",
          });
          continue;
        }
        result.set(hotel.index, personalization);
        // Store with hotelId for correct cache reconstruction regardless of order
        indexedPersonalizations.push({ ...personalization, hotelId });
      }

      // Fill gaps for any hotels the AI skipped to keep result and cache aligned
      hotels.forEach((hotel, index) => {
        if (result.has(index)) return;

        const fallback = getDefaultPersonalization(hotel);
        result.set(index, fallback);

        const hotelId = hotelIds[index];
        if (!hotelId) {
          recordTelemetryEvent("ai.hotel.personalize.missing_hotel_id", {
            attributes: { hotelCount: hotels.length, index },
            level: "warning",
          });
          return;
        }

        indexedPersonalizations.push({ ...fallback, hotelId });
      });

      // Cache indexed results to preserve hotel indices
      await setCachedJson(cacheKey, indexedPersonalizations, PERSONALIZATION_CACHE_TTL);

      return result;
    }
  );
}

/**
 * Removes cached hotel personalization results for a specific user, hotel set, and preferences.
 *
 * Call this when hotel data changes (pricing, amenities, availability) to trigger fresh AI generation.
 * The cache key combines user ID, sorted hotel identifiers, and preference hash.
 *
 * @param userId - Unique user identifier
 * @param hotels - Array of hotels to invalidate cache for
 * @param preferences - User's travel preferences affecting personalization
 * @returns Promise resolving when cache is deleted
 * @throws Error if hotels array exceeds maximum allowed size (20)
 */
export async function invalidatePersonalizationCache(
  userId: string,
  hotels: HotelForPersonalization[],
  preferences: UserPreferences
): Promise<void> {
  if (hotels.length === 0) return;
  if (hotels.length > MAX_HOTELS_PER_REQUEST) {
    throw new Error(
      `Cannot invalidate personalization cache for more than ${MAX_HOTELS_PER_REQUEST} hotels`
    );
  }
  const hotelIds = buildHotelIdentifiers(hotels);
  const cacheKey = buildPersonalizationCacheKey(userId, hotelIds, preferences);
  await deleteCachedJson(cacheKey);
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
