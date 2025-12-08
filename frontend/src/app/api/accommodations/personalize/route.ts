/**
 * @fileoverview AI-powered hotel personalization endpoint.
 *
 * Generates personalized recommendations for hotels based on user preferences:
 * - Personalized tags
 * - Match explanations
 * - Recommendation scores (1-10)
 * - Vibe classifications
 */

import "server-only";

import {
  getDefaultPersonalization,
  type HotelForPersonalization,
  personalizeHotels,
} from "@ai/services/hotel-personalization";
import {
  type HotelPersonalizeRequest,
  hotelPersonalizeRequestSchema,
} from "@schemas/api";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { requireUserId } from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";

/**
 * POST /api/accommodations/personalize
 *
 * Personalizes hotels for the authenticated user based on their preferences.
 * Results are cached per-user for 30 minutes.
 *
 * @param req - Next.js request object
 * @param context - Route context with user and supabase client
 * @param validated - Validated request body
 * @returns JSON response with personalized hotel recommendations
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "accommodations:personalize",
  schema: hotelPersonalizeRequestSchema,
  telemetry: "accommodations.personalize",
})(async (_req: NextRequest, { user }, validated: HotelPersonalizeRequest) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;
  const logger = createServerLogger("api.accommodations.personalize");

  // Convert request hotels to service format
  const hotelsForPersonalization: HotelForPersonalization[] = validated.hotels.map(
    (h) => ({
      amenities: h.amenities,
      brand: h.brand,
      category: h.category,
      location: h.location,
      name: h.name,
      pricePerNight: h.pricePerNight,
      rating: h.rating,
      starRating: h.starRating,
    })
  );

  try {
    // Attempt AI personalization
    const personalizations = await personalizeHotels(
      userId,
      hotelsForPersonalization,
      validated.preferences
    );

    // Build response with fallbacks for missing personalizations
    const results = validated.hotels.map((hotel, index) => {
      const personalization = personalizations.get(index);
      if (personalization) {
        return { hotelName: hotel.name, ...personalization };
      }
      // Fallback to default personalization
      const defaultResult = getDefaultPersonalization(hotelsForPersonalization[index]);
      return { hotelName: hotel.name, ...defaultResult };
    });

    return NextResponse.json({ results });
  } catch (error) {
    // Log error and return fallback with proper error status
    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    logger.error("Personalization failed", {
      error: errorMessage,
      hotelCount: hotelsForPersonalization.length,
      userId,
    });

    // Return default personalizations with 503 status to indicate service degradation
    const results = hotelsForPersonalization.map((hotel) => ({
      hotelName: hotel.name,
      ...getDefaultPersonalization(hotel),
    }));

    return NextResponse.json(
      {
        error: "ai_service_unavailable",
        fallback: true,
        message: "AI service unavailable, please try again later",
        results,
      },
      { status: 503 }
    );
  }
});
