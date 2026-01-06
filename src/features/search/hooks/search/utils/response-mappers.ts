/**
 * @fileoverview Response mappers for transforming API responses to SearchResults format.
 */

import { getCategoryFromChainCode } from "@domain/amadeus/chain-codes";
import type {
  Accommodation,
  Activity,
  Flight,
  SearchParams,
  SearchResults,
  SearchType,
} from "@schemas/search";

// ===== FLIGHT MAPPERS =====

interface FlightItinerary {
  id: string;
  price: number;
  segments: Array<{
    arrival?: string;
    carrier?: string;
    departure?: string;
    destination: string;
    flightNumber?: string;
    origin: string;
  }>;
}

interface FlightOffer {
  id: string;
  price: { amount: number; currency: string };
  slices: Array<{
    cabinClass: string;
    segments: Array<{
      arrivalTime?: string;
      carrier?: string;
      departureTime?: string;
      destination: { iata: string };
      durationMinutes?: number;
      flightNumber?: string;
      origin: { iata: string };
    }>;
  }>;
}

interface FlightApiResponse {
  currency?: string;
  itineraries?: FlightItinerary[];
  offers?: FlightOffer[];
}

/**
 * Maps flight API response (FlightSearchResult) to SearchResults format.
 */
export function mapFlightResponse(data: FlightApiResponse): Flight[] {
  // Prefer itineraries if available, fall back to offers
  if (data.itineraries && data.itineraries.length > 0) {
    return data.itineraries
      .filter((itinerary) => itinerary.segments && itinerary.segments.length > 0)
      .map((itinerary) => {
        const firstSegment = itinerary.segments[0];
        const lastSegment = itinerary.segments[itinerary.segments.length - 1];
        const totalDuration = itinerary.segments.reduce((sum, seg) => {
          // Estimate duration from departure/arrival if available
          const deptTs = seg.departure ? Date.parse(seg.departure) : Number.NaN;
          const arrTs = seg.arrival ? Date.parse(seg.arrival) : Number.NaN;
          if (!Number.isFinite(deptTs) || !Number.isFinite(arrTs) || arrTs < deptTs) {
            return sum;
          }
          return sum + Math.round((arrTs - deptTs) / 60000);
        }, 0);

        return {
          airline: firstSegment?.carrier ?? "Unknown",
          arrivalTime: lastSegment?.arrival ?? "",
          departureTime: firstSegment?.departure ?? "",
          destination: lastSegment?.destination ?? "",
          duration: totalDuration || 0,
          flightNumber: firstSegment?.flightNumber ?? "",
          id: itinerary.id,
          origin: firstSegment?.origin ?? "",
          price: itinerary.price,
          stops: itinerary.segments.length - 1,
        };
      });
  }

  // Map offers to Flight format
  if (data.offers && data.offers.length > 0) {
    return data.offers
      .filter(
        (offer) =>
          offer.slices &&
          offer.slices.length > 0 &&
          offer.slices[0]?.segments &&
          offer.slices[0].segments.length > 0
      )
      .map((offer) => {
        const firstSlice = offer.slices[0];
        const firstSegment = firstSlice.segments[0];
        const lastSegment = firstSlice.segments[firstSlice.segments.length - 1];
        const totalDuration = firstSlice?.segments.reduce(
          (sum, seg) => sum + (seg.durationMinutes ?? 0),
          0
        );

        return {
          airline: firstSegment?.carrier ?? "Unknown",
          arrivalTime: lastSegment?.arrivalTime ?? "",
          cabinClass: firstSlice?.cabinClass ?? undefined,
          departureTime: firstSegment?.departureTime ?? "",
          destination: lastSegment?.destination.iata ?? "",
          duration: totalDuration ?? 0,
          flightNumber: firstSegment?.flightNumber ?? "",
          id: offer.id,
          origin: firstSegment?.origin.iata ?? "",
          price: offer.price.amount,
          stops: (firstSlice?.segments.length ?? 1) - 1,
        };
      });
  }

  return [];
}

// ===== ACCOMMODATION MAPPERS =====

interface AccommodationListingResponse {
  address?: { cityName?: string; lines?: string[] };
  amenities?: string[];
  cancellationPolicy?: {
    deadline?: string;
    description?: string;
    refundable?: boolean;
  };
  chainCode?: string;
  geoCode?: { latitude: number; longitude: number };
  hotel?: { hotelId?: string; name?: string };
  id?: string | number;
  name?: string;
  place?: { rating?: number; userRatingCount?: number };
  rooms?: Array<{
    rates?: Array<{
      price?: {
        base?: string | number;
        currency?: string;
        total?: string | number;
      };
    }>;
    roomsLeft?: number;
  }>;
  starRating?: number;
  taxes?: number;
}

interface AccommodationApiResponse {
  listings?: AccommodationListingResponse[];
}

/**
 * Calculate urgency level based on rooms left.
 */
function calculateUrgency(roomsLeft: number | undefined): "low" | "medium" | "high" {
  if (roomsLeft === undefined) return "medium";
  if (roomsLeft <= 2) return "high";
  if (roomsLeft <= 5) return "medium";
  return "low";
}

/**
 * Maps accommodation API response to SearchResults format.
 * Preserves provider data for UI enrichment (availability, policies, taxes).
 */
export function mapAccommodationResponse(
  data: AccommodationApiResponse,
  searchParams: SearchParams
): Accommodation[] {
  if (!data.listings) return [];

  // Extract check-in/check-out from search params if available
  const accommodationParams = searchParams as {
    checkin?: string;
    checkout?: string;
    checkIn?: string;
    checkOut?: string;
    currency?: string;
  };
  const checkIn = accommodationParams.checkin ?? accommodationParams.checkIn ?? "";
  const checkOut = accommodationParams.checkout ?? accommodationParams.checkOut ?? "";

  return data.listings
    .filter((listing) => listing.hotel?.name || listing.name)
    .map((listing) => {
      const name = listing.hotel?.name ?? listing.name ?? "Unknown";
      const id = String(listing.hotel?.hotelId ?? listing.id ?? name);
      const addressLines = listing.address?.lines ?? [];
      const city = listing.address?.cityName ?? "";
      const location = [...addressLines, city].filter(Boolean).join(", ") || name;

      // Extract price from first room's first rate
      const firstRoom = listing.rooms?.[0];
      const firstRate = firstRoom?.rates?.[0];
      const parsedTotalPrice =
        typeof firstRate?.price?.total === "string"
          ? Number.parseFloat(firstRate.price.total)
          : undefined;
      const totalPrice =
        typeof parsedTotalPrice === "number" && Number.isFinite(parsedTotalPrice)
          ? parsedTotalPrice
          : 0;
      const currency =
        firstRate?.price?.currency ?? accommodationParams.currency ?? "USD";
      const rating = listing.place?.rating ?? listing.starRating ?? 0;

      // Extract roomsLeft from first room (Amadeus provides per-room availability)
      const roomsLeft = firstRoom?.roomsLeft;

      // Calculate nights for price per night
      let nights = 1;
      if (checkIn && checkOut) {
        const checkInDate = new Date(checkIn);
        const checkOutDate = new Date(checkOut);
        if (
          Number.isNaN(checkInDate.getTime()) ||
          Number.isNaN(checkOutDate.getTime())
        ) {
          nights = 1;
        } else {
          nights = Math.max(
            1,
            Math.ceil(
              (checkOutDate.getTime() - checkInDate.getTime()) / (1000 * 60 * 60 * 24)
            )
          );
        }
      }
      const pricePerNight = totalPrice > 0 ? totalPrice / nights : 0;
      const category = getCategoryFromChainCode(listing.chainCode);

      return {
        address: listing.address,
        amenities: listing.amenities ?? [],
        availability: {
          flexible: listing.cancellationPolicy?.refundable,
          roomsLeft,
          urgency: calculateUrgency(roomsLeft),
        },
        category,
        chainCode: listing.chainCode,
        checkIn,
        checkOut,
        coordinates: listing.geoCode
          ? { lat: listing.geoCode.latitude, lng: listing.geoCode.longitude }
          : undefined,
        currency,
        id,
        images: [],
        location,
        name,
        policies: listing.cancellationPolicy
          ? { cancellation: listing.cancellationPolicy }
          : undefined,
        pricePerNight,
        rating,
        starRating: listing.starRating,
        taxes: listing.taxes,
        totalPrice: Number.isFinite(parsedTotalPrice)
          ? (parsedTotalPrice as number)
          : pricePerNight * nights,
        type: "hotel",
      };
    });
}

// ===== ACTIVITY MAPPERS =====

interface ActivityApiResponse {
  activities?: Activity[];
  metadata?: { total?: number };
}

/**
 * Maps activity API response to SearchResults format.
 */
export function mapActivityResponse(data: ActivityApiResponse): Activity[] {
  return data.activities ?? [];
}

// ===== UTILITY FUNCTIONS =====

function assertUnreachable(_value: never): never {
  throw new Error("Unhandled search type");
}

/**
 * Returns empty results for a search type (used for graceful failure).
 */
export function getEmptyResults(searchType: SearchType): SearchResults {
  switch (searchType) {
    case "activity":
      return { activities: [] };
    case "flight":
      return { flights: [] };
    case "accommodation":
      return { accommodations: [] };
    case "destination":
      return { destinations: [] };
    default:
      return assertUnreachable(searchType);
  }
}

// ===== API ENDPOINTS =====

export const SEARCH_ENDPOINTS: Record<SearchType, string> = {
  accommodation: "/api/accommodations/search",
  activity: "/api/activities/search",
  destination: "/api/places/search",
  flight: "/api/flights/search",
};
