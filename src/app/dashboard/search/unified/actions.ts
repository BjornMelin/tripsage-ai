/**
 * @fileoverview Server action for unified hotel search.
 */

"use server";

import "server-only";

import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "@domain/accommodations/constants";
import { AmadeusProviderAdapter } from "@domain/accommodations/providers/amadeus-adapter";
import { AccommodationsService } from "@domain/accommodations/service";
import { accommodationListingSchema } from "@schemas/accommodations";
import {
  type HotelResult,
  type HotelSearchFormData,
  type SearchAccommodationParams,
  searchAccommodationParamsSchema,
} from "@schemas/search";
import { format } from "date-fns";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { bumpTag, versionedKey } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { FALLBACK_HOTEL_IMAGE } from "@/lib/constants/images";
import { getGoogleMapsBrowserKey } from "@/lib/env/server";
import { enrichHotelListingWithPlaces } from "@/lib/google/places-enrichment";
import { resolveLocationToLatLng } from "@/lib/google/places-geocoding";
import { retryWithBackoff } from "@/lib/http/retry";
import { secureUuid } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const MAX_SEARCH_RESULTS = 10;
const logger = createServerLogger("search.unified.actions");

/** Build photo URL. */
function buildPhotoUrl(photoName?: string): string | undefined {
  if (!photoName) return undefined;
  // This URL is consumed by the client; use the public browser key (referrer-restricted),
  // not a privileged server key.
  const apiKey = getGoogleMapsBrowserKey();
  if (!apiKey) return undefined;
  return `https://places.googleapis.com/v1/${photoName}/media?maxHeightPx=800&maxWidthPx=1200&key=${apiKey}`;
}

/**
 * Search hotels with schema validation.
 *
 * Maps component HotelSearchFormData to SearchAccommodationParams schema and validates.
 *
 * @param params - Hotel search parameters from component.
 * @returns Array of hotel results.
 * @throws Error if validation fails.
 */
export async function searchHotelsAction(
  params: HotelSearchFormData
): Promise<HotelResult[]> {
  // Map component params to schema format
  const schemaParams: SearchAccommodationParams = {
    adults: params.adults,
    amenities: params.amenities,
    checkIn: params.checkIn,
    checkOut: params.checkOut,
    children: params.children,
    currency: params.currency,
    destination: params.location,
    minRating: params.rating,
    priceRange: params.priceRange,
  };

  const validation = searchAccommodationParamsSchema.safeParse(schemaParams);
  if (!validation.success) {
    await withTelemetrySpan(
      "ui.unified.searchHotels.validation_failed",
      {
        attributes: {
          issueCount: validation.error.issues.length,
        },
      },
      () => undefined
    );
    throw new Error("Invalid hotel search parameters");
  }

  const validatedParams = validation.data;
  const service = new AccommodationsService({
    bumpTag,
    cacheTtlSeconds: ACCOM_SEARCH_CACHE_TTL_SECONDS,
    canonicalizeParamsForCache,
    enrichHotelListingWithPlaces,
    getCachedJson,
    provider: new AmadeusProviderAdapter(),
    resolveLocationToLatLng,
    retryWithBackoff,
    setCachedJson,
    supabase: createServerSupabase,
    versionedKey,
  });
  const today = new Date();
  const todayIso = format(today, "yyyy-MM-dd");
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const tomorrowIso = format(tomorrow, "yyyy-MM-dd");
  const effectiveCheckIn = validatedParams.checkIn ?? todayIso;
  const effectiveCheckOut = validatedParams.checkOut ?? tomorrowIso;
  const searchResult = await withTelemetrySpan(
    "ui.unified.searchHotels",
    { attributes: { location: validatedParams.destination ?? "" } },
    async () =>
      await service.search(
        {
          checkin: effectiveCheckIn,
          checkout: effectiveCheckOut,
          guests: (validatedParams.adults ?? 1) + (validatedParams.children ?? 0),
          location: validatedParams.destination ?? "",
          priceMax: validatedParams.priceRange?.max,
          priceMin: validatedParams.priceRange?.min,
          semanticQuery: validatedParams.destination ?? "",
        },
        {
          sessionId: secureUuid(),
        }
      )
  );

  /** Compute nights for the effective check-in/check-out window. */
  const calculateNights = (): number => {
    const start = new Date(effectiveCheckIn);
    const end = new Date(effectiveCheckOut);
    const diffMs = end.getTime() - start.getTime();
    const rawNights = diffMs / (1000 * 60 * 60 * 24);
    if (!Number.isFinite(rawNights)) return 1;
    return Math.max(1, Math.ceil(rawNights));
  };
  const nights = calculateNights();

  /** Map search results to unified hotel results. */
  return (searchResult.listings ?? [])
    .slice(0, MAX_SEARCH_RESULTS)
    .map((listing, index) => {
      // Parse listing with Zod schema for type safety
      const parseResult = accommodationListingSchema.safeParse(listing);
      if (!parseResult.success) {
        logger.warn("accommodation listing parse failed", {
          currency: validatedParams.currency ?? "USD",
          index,
          issues: parseResult.error.format(),
        });
        // Fallback to minimal hotel result if parsing fails
        return {
          ai: {
            personalizedTags: ["hybrid-amadeus", "google-places"],
            reason: "Real-time Amadeus pricing with Places enrichment",
            recommendation: 8,
          },
          amenities: { essential: [], premium: [], unique: [] },
          availability: { flexible: true, roomsLeft: 3, urgency: "medium" },
          category: "hotel" as const,
          guestExperience: { highlights: [], recentMentions: [], vibe: "business" },
          id: secureUuid(),
          images: {
            count: 1,
            gallery: [],
            main: FALLBACK_HOTEL_IMAGE,
          },
          location: {
            address: "",
            city: "",
            coordinates: undefined,
            district: "",
            landmarks: [],
          },
          name: "Hotel",
          pricing: {
            basePrice: 0,
            currency: validatedParams.currency ?? "USD",
            priceHistory: "stable",
            pricePerNight: 0,
            taxes: 0,
            taxesEstimated: true,
            totalPrice: 0,
          },
          reviewCount: 0,
          starRating: 0,
          sustainability: { certified: false, practices: [], score: 0 },
          userRating: 0,
        } satisfies HotelResult;
      }

      const hotel = parseResult.data;
      const addressLines = hotel.address?.lines ?? [];
      const amenities = hotel.amenities ?? [];
      const firstRoom = hotel.rooms?.[0];
      const firstRate = firstRoom?.rates?.[0];
      const ratePrice = firstRate?.price;

      const totalNumeric = ratePrice
        ? Number.parseFloat(String(ratePrice.total ?? ratePrice.numeric ?? "0"))
        : 0;
      const pricePerNight =
        totalNumeric && nights > 0
          ? Math.round((totalNumeric / nights) * 100) / 100
          : 0;

      const photoName =
        hotel.placeDetails?.photos?.[0]?.name ?? hotel.place?.photos?.[0]?.name;
      const mainImage = buildPhotoUrl(photoName) ?? FALLBACK_HOTEL_IMAGE;

      const starRating = hotel.starRating ?? 0;
      return {
        ai: {
          personalizedTags: ["hybrid-amadeus", "google-places"],
          reason: "Real-time Amadeus pricing with Places enrichment",
          recommendation: 8,
        },
        amenities: {
          essential: amenities,
          premium: [],
          unique: [],
        },
        availability: {
          flexible: true,
          roomsLeft: firstRoom?.roomsLeft ?? 3,
          urgency: "medium",
        },
        category: "hotel",
        guestExperience: {
          highlights: [],
          recentMentions: [],
          vibe: "business",
        },
        id: String(hotel.id ?? hotel.hotel?.hotelId ?? secureUuid()),
        images: {
          count: 1,
          gallery: mainImage ? [mainImage] : [],
          main: mainImage,
        },
        location: {
          address: addressLines.join(", "),
          city: hotel.address?.cityName ?? hotel.searchMeta?.location ?? "",
          coordinates: hotel.geoCode
            ? { lat: hotel.geoCode.latitude, lng: hotel.geoCode.longitude }
            : undefined,
          district: "",
          landmarks: [],
          walkScore: undefined,
        },
        name: hotel.name ?? hotel.hotel?.name ?? "Hotel",
        pricing: {
          basePrice: ratePrice
            ? Number.parseFloat(String(ratePrice.base ?? pricePerNight))
            : 0,
          currency: ratePrice?.currency ?? validatedParams.currency ?? "USD",
          priceHistory: "stable",
          pricePerNight,
          taxes: ratePrice?.taxes?.[0]?.amount
            ? Number.parseFloat(String(ratePrice.taxes[0].amount))
            : 0,
          taxesEstimated: !ratePrice?.taxes?.[0]?.amount,
          totalPrice: totalNumeric,
        },
        reviewCount: hotel.place?.userRatingCount ?? 0,
        starRating,
        sustainability: {
          certified: false,
          practices: [],
          score: 0,
        },
        userRating: hotel.place?.rating ?? 0,
      } satisfies HotelResult;
    });
}
