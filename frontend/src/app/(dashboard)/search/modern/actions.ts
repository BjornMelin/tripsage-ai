/**
 * @fileoverview Server action for modern hotel search.
 */

"use server";

import "server-only";

import { getAccommodationsService } from "@domain/accommodations/container";
import type { ModernHotelSearchParams } from "@/components/features/search/hotel-search-form";
import type { ModernHotelResult } from "@/components/features/search/modern-hotel-results";
import { getGoogleMapsBrowserKey } from "@/lib/env/client";
import { secureUuid } from "@/lib/security/random";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Search parameters. */
type SearchParams = ModernHotelSearchParams & { currency?: string };

/** Build photo URL. */
function buildPhotoUrl(photoName?: string): string | undefined {
  if (!photoName) return undefined;
  const apiKey = getGoogleMapsBrowserKey();
  if (!apiKey) return undefined;
  return `https://places.googleapis.com/v1/${photoName}/media?maxHeightPx=800&maxWidthPx=1200&key=${apiKey}`;
}

/** Search hotels. */
export async function searchHotelsAction(
  params: SearchParams
): Promise<ModernHotelResult[]> {
  const service = getAccommodationsService();
  const searchResult = await withTelemetrySpan(
    "ui.modern.searchHotels",
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

  /** Calculate nights. */
  const nights =
    params.checkIn && params.checkOut
      ? Math.max(
          1,
          Math.ceil(
            (new Date(params.checkOut).getTime() - new Date(params.checkIn).getTime()) /
              (1000 * 60 * 60 * 24)
          )
        )
      : 1;

  /** Map search results to modern hotel results. */
  return (searchResult.listings ?? []).slice(0, 10).map((listing) => {
    const hotel = listing as Record<string, unknown>;
    const address = hotel.address as
      | { lines?: string[]; cityName?: string }
      | undefined;
    const addressLines = address?.lines ?? [];
    const providerHotel = hotel.hotel as
      | { hotelId?: string; name?: string }
      | undefined;
    const amenities = (hotel.amenities as string[] | undefined) ?? [];
    const rooms = (hotel.rooms as Array<Record<string, unknown>> | undefined) ?? [];
    const firstRoom = rooms[0] ?? {};
    const rates = (firstRoom.rates as Array<Record<string, unknown>> | undefined) ?? [];
    const firstRate = rates[0] ?? {};
    const ratePrice = (firstRate.price as Record<string, unknown>) ?? {};
    const totalNumeric = Number.parseFloat(
      (ratePrice.total as string | undefined) ??
        (ratePrice.numeric as string | undefined) ??
        "0"
    );
    const pricePerNight =
      totalNumeric && nights > 0 ? Number(totalNumeric / nights).toFixed(2) : "0";
    const photoName =
      ((hotel.placeDetails as { photos?: Array<{ name?: string }> } | undefined)
        ?.photos ?? [])[0]?.name ??
      ((hotel.place as { photos?: Array<{ name?: string }> } | undefined)?.photos ??
        [])[0]?.name ??
      undefined;
    const mainImage =
      buildPhotoUrl(photoName) ??
      "https://images.unsplash.com/photo-1501117716987-c8e1ecb210af?auto=format&fit=crop&w=800&q=80";

    const place = hotel.place as
      | { rating?: number; userRatingCount?: number }
      | undefined;
    const starRating = (hotel.starRating as number | undefined) ?? 0;
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
        roomsLeft: Number((firstRoom as { roomsLeft?: number }).roomsLeft ?? 3),
        urgency: "medium",
      },
      category: "hotel",
      guestExperience: {
        highlights: [],
        recentMentions: [],
        vibe: "business",
      },
      id: String(hotel.id ?? providerHotel?.hotelId ?? secureUuid()),
      images: {
        count: 1,
        gallery: mainImage ? [mainImage] : [],
        main: mainImage,
      },
      location: {
        address: addressLines.join(", "),
        city:
          address?.cityName ??
          (hotel.searchMeta as { location?: string } | undefined)?.location ??
          "",
        district: "",
        landmarks: [],
        walkScore: undefined,
      },
      name: (hotel.name as string | undefined) ?? providerHotel?.name ?? "Hotel",
      pricing: {
        basePrice: Number.parseFloat(
          (ratePrice.base as string | undefined) ?? pricePerNight ?? "0"
        ),
        currency:
          (ratePrice.currency as string | undefined) ?? params.currency ?? "USD",
        priceHistory: "stable",
        pricePerNight: Number(pricePerNight),
        taxes: Number.parseFloat(
          (((ratePrice.taxes as Array<Record<string, string>> | undefined) ?? [])[0]
            ?.amount ?? "0") as string
        ),
        totalPrice: totalNumeric,
      },
      reviewCount: place?.userRatingCount ?? 0,
      starRating,
      sustainability: {
        certified: false,
        practices: [],
        score: 0,
      },
      userRating: place?.rating ?? 0,
    } satisfies ModernHotelResult;
  });
}
