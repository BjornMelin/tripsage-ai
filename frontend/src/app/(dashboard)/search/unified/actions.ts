/**
 * @fileoverview Server action for unified hotel search.
 */

"use server";

import "server-only";

import { getAccommodationsService } from "@domain/accommodations/container";
import { accommodationListingSchema } from "@schemas/accommodations";
import type { HotelResult } from "@/components/features/search/hotel-results";
import type { HotelSearchParams } from "@/components/features/search/hotel-search-form";
import { getGoogleMapsBrowserKey } from "@/lib/env/client";
import { secureUuid } from "@/lib/security/random";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Search parameters. */
type SearchParams = HotelSearchParams & { currency?: string };

/** Build photo URL. */
function buildPhotoUrl(photoName?: string): string | undefined {
  if (!photoName) return undefined;
  const apiKey = getGoogleMapsBrowserKey();
  if (!apiKey) return undefined;
  return `https://places.googleapis.com/v1/${photoName}/media?maxHeightPx=800&maxWidthPx=1200&key=${apiKey}`;
}

/** Search hotels. */
export async function searchHotelsAction(params: SearchParams): Promise<HotelResult[]> {
  const service = getAccommodationsService();
  const searchResult = await withTelemetrySpan(
    "ui.unified.searchHotels",
    { attributes: { location: params.location } },
    async () =>
      await service.search(
        {
          checkin: params.checkIn,
          checkout: params.checkOut,
          guests: params.adults + params.children,
          location: params.location,
          priceMax: params.priceRange.max,
          priceMin: params.priceRange.min,
          semanticQuery: params.location,
        },
        {
          sessionId: secureUuid(),
        }
      )
  );

  /** Calculate nights with guards. */
  const calculateNights = (): number => {
    if (!params.checkIn || !params.checkOut) return 1;
    const start = new Date(params.checkIn);
    const end = new Date(params.checkOut);
    const diffMs = end.getTime() - start.getTime();
    const rawNights = diffMs / (1000 * 60 * 60 * 24);
    if (!Number.isFinite(rawNights)) return 1;
    return Math.max(1, Math.ceil(rawNights));
  };
  const nights = calculateNights();

  /** Map search results to unified hotel results. */
  return (searchResult.listings ?? []).slice(0, 10).map((listing) => {
    // Parse listing with Zod schema for type safety
    const parseResult = accommodationListingSchema.safeParse(listing);
    if (!parseResult.success) {
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
          main: "https://images.unsplash.com/photo-1501117716987-c8e1ecb210af?auto=format&fit=crop&w=800&q=80",
        },
        location: { address: "", city: "", district: "", landmarks: [] },
        name: "Hotel",
        pricing: {
          basePrice: 0,
          currency: params.currency ?? "USD",
          priceHistory: "stable",
          pricePerNight: 0,
          taxes: 0,
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
      totalNumeric && nights > 0 ? Number(totalNumeric / nights).toFixed(2) : "0";

    const photoName =
      hotel.placeDetails?.photos?.[0]?.name ?? hotel.place?.photos?.[0]?.name;
    const mainImage =
      buildPhotoUrl(photoName) ??
      "https://images.unsplash.com/photo-1501117716987-c8e1ecb210af?auto=format&fit=crop&w=800&q=80";

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
        district: "",
        landmarks: [],
        walkScore: undefined,
      },
      name: hotel.name ?? hotel.hotel?.name ?? "Hotel",
      pricing: {
        basePrice: ratePrice
          ? Number.parseFloat(String(ratePrice.base ?? pricePerNight ?? "0"))
          : 0,
        currency: ratePrice?.currency ?? params.currency ?? "USD",
        priceHistory: "stable",
        pricePerNight: Number(pricePerNight),
        taxes: ratePrice?.taxes?.[0]?.amount
          ? Number.parseFloat(String(ratePrice.taxes[0].amount))
          : 0,
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
