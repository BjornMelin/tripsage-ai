/**
 * @fileoverview Pure mapping utilities for hotel/accommodation search results.
 */

import type { Accommodation, HotelResult } from "@schemas/search";
import { FALLBACK_HOTEL_IMAGE } from "@/lib/constants/images";
import { categorizeAmenities } from "@/lib/utils/amenity-categorization";

type AccommodationLike = Accommodation & {
  category?: string;
  district?: string;
  reviewCount?: number;
  address?: (Accommodation["address"] & { district?: string }) | undefined;
};

const ALLOWED_CATEGORIES = [
  "hotel",
  "resort",
  "apartment",
  "villa",
  "boutique",
  "hostel",
] as const;

type AllowedCategory = (typeof ALLOWED_CATEGORIES)[number];

type HotelVibe = "luxury" | "business" | "family" | "romantic" | "adventure";

function toAllowedCategory(category?: string): AllowedCategory {
  if (!category) return "hotel";
  return ALLOWED_CATEGORIES.includes(category as AllowedCategory)
    ? (category as AllowedCategory)
    : "hotel";
}

function deriveVibe(category: AllowedCategory, normalizedAmenities: string): HotelVibe {
  if (category === "resort" || normalizedAmenities.includes("spa")) return "luxury";
  if (normalizedAmenities.includes("kid") || normalizedAmenities.includes("family")) {
    return "family";
  }
  if (
    normalizedAmenities.includes("hiking") ||
    normalizedAmenities.includes("surf") ||
    normalizedAmenities.includes("rafting") ||
    normalizedAmenities.includes("adventure") ||
    normalizedAmenities.includes("outdoor")
  ) {
    return "adventure";
  }
  if (category === "boutique") return "romantic";
  return "business";
}

// Returns a score on a 1–10 scale (default 5 = neutral); rating is mapped by
// Math.round(rating * 2) and clamped to [1,10].
function getRecommendationScore(rating: number | undefined): number {
  if (typeof rating !== "number") return 5;
  return Math.max(1, Math.min(10, Math.round(rating * 2)));
}

function normalizeStarRating(starRating: number | undefined): number | undefined {
  if (starRating == null) return undefined;
  if (starRating < 1 || starRating > 5) return undefined;
  return starRating;
}

/**
 * Maps an accommodation search result into the unified `HotelResult` UI shape.
 *
 * Intentionally pure (no store reads, no network, no time-dependent logic) to
 * enable reuse and focused unit tests.
 */
export function mapAccommodationToHotelResult(
  accommodation: AccommodationLike
): HotelResult {
  const name =
    accommodation.name.trim().length > 0 ? accommodation.name : accommodation.id;

  const pricePerNight =
    Number.isFinite(accommodation.pricePerNight) && accommodation.pricePerNight >= 0
      ? accommodation.pricePerNight
      : 0;

  const totalPrice =
    Number.isFinite(accommodation.totalPrice) && accommodation.totalPrice >= 0
      ? accommodation.totalPrice
      : pricePerNight;

  const taxesRaw = accommodation.taxes;
  const taxes =
    typeof taxesRaw === "number" && Number.isFinite(taxesRaw) && taxesRaw >= 0
      ? taxesRaw
      : 0;
  const taxesEstimated = taxesRaw === undefined || taxes !== taxesRaw;

  const coordinatesRaw = accommodation.coordinates;
  const latitude = coordinatesRaw?.lat;
  const longitude = coordinatesRaw?.lng;
  const hasValidLatLng =
    typeof latitude === "number" &&
    typeof longitude === "number" &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180;
  const coordinates = hasValidLatLng ? coordinatesRaw : undefined;

  const roomsLeft = accommodation.availability?.roomsLeft;
  const urgency = accommodation.availability?.urgency ?? "medium";
  const flexible =
    accommodation.availability?.flexible ??
    accommodation.policies?.cancellation?.refundable ??
    false;

  const amenityList = accommodation.amenities ?? [];
  const { essential, premium, unique, normalizedString } =
    categorizeAmenities(amenityList);
  const personalizedTags = [...essential, ...premium, ...unique].slice(0, 3);

  const category = toAllowedCategory(accommodation.category);
  const vibe = deriveVibe(category, normalizedString);

  const addressLines = accommodation.address?.lines ?? [];
  const city = accommodation.address?.cityName ?? accommodation.location ?? "";
  const address =
    addressLines.length > 0 ? addressLines.join(", ") : (accommodation.location ?? "");
  const district = accommodation.address?.district ?? accommodation.district;
  const reviewCount = accommodation.reviewCount ?? 0;

  const recommendation = getRecommendationScore(accommodation.rating);

  return {
    ai: {
      personalizedTags,
      reason: city ? `Great ${category} option in ${city}` : `Great ${category} option`,
      recommendation,
    },
    amenities: {
      essential: essential.slice(0, 3),
      premium: premium.slice(0, 3),
      unique: unique.slice(0, 3),
    },
    availability: {
      flexible,
      roomsLeft,
      urgency,
    },
    brand: undefined,
    category,
    guestExperience: {
      highlights: [],
      recentMentions: [],
      vibe,
    },
    id: accommodation.id,
    images: {
      count: accommodation.images?.length ?? 0,
      gallery: accommodation.images ?? [],
      main: accommodation.images?.[0] ?? FALLBACK_HOTEL_IMAGE,
    },
    location: {
      address,
      city,
      coordinates,
      district,
      landmarks: [],
      walkScore: undefined,
    },
    name,
    pricing: {
      basePrice: pricePerNight,
      currency: accommodation.currency ?? "USD",
      priceHistory: "unknown",
      pricePerNight,
      taxes,
      taxesEstimated,
      totalPrice,
    },
    reviewCount,
    starRating: normalizeStarRating(accommodation.starRating),
    sustainability: {
      certified: false,
      practices: [],
      score: 5,
    },
    userRating: accommodation.rating,
  };
}
