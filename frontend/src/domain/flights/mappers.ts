/**
 * @fileoverview Provider mappers for flights.
 * Converts provider payloads to normalized FlightOffer DTOs.
 */

import { FLIGHT_OFFER_SCHEMA, type FlightOffer } from "@schemas/flights";

/** The type of the Duffel money. */
type DuffelMoney = {
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  total_amount?: string;
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  total_currency?: string;
};

/** The type of the Duffel location. */
type DuffelLocation = {
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  iata_code?: string;
  name?: string;
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  city_name?: string;
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  country_name?: string;
  terminal?: string;
};

/** The type of the Duffel segment. */
type DuffelSegment = {
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  arriving_at?: string;
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  departing_at?: string;
  destination?: DuffelLocation;
  origin?: DuffelLocation;
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  marketing_carrier?: { iata_code?: string; name?: string; id?: string };
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  operating_carrier?: { iata_code?: string; name?: string; id?: string };
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  marketing_carrier_flight_number?: string;
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  operating_carrier_flight_number?: string;
  distance?: number;
  duration?: string;
};

/** The type of the Duffel slice. */
type DuffelSlice = {
  // biome-ignore lint/style/useNamingConvention: external provider payloads use snake_case
  cabin_class?: string;
  duration?: string;
  segments?: DuffelSegment[];
};

/** The type of the Duffel offer. */
type DuffelOffer = DuffelMoney & {
  id?: string;
  slices?: DuffelSlice[];
};

/**
 * Parse a Duffel ISO-8601 duration (PnDTnHnM) to minutes.
 *
 * @param value - The ISO-8601 duration.
 * @returns The duration in minutes or undefined on parse errors.
 */
function parseIsoDurationToMinutes(value?: string): number | undefined {
  if (!value || typeof value !== "string") return undefined;
  const match = /P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?/i.exec(value);
  if (!match) return undefined;
  const days = Number(match[1] ?? 0);
  const hours = Number(match[2] ?? 0);
  const minutes = Number(match[3] ?? 0);
  return days * 24 * 60 + hours * 60 + minutes;
}

/**
 * Normalize one Duffel offer into the shared FlightOffer shape.
 *
 * @param offer - The Duffel offer.
 * @returns The normalized FlightOffer or null on parse errors.
 */
export function mapDuffelOffer(offer: DuffelOffer): FlightOffer | null {
  if (!offer?.id) return null;
  const currency = offer.total_currency ?? "USD";
  const amount = Number(offer.total_amount ?? 0);
  const slices = Array.isArray(offer.slices) ? offer.slices : [];

  const normalizedSlices = slices
    .map((slice): FlightOffer["slices"][number] | null => {
      const segments = Array.isArray(slice.segments) ? slice.segments : [];
      const normalizedSegments: FlightOffer["slices"][number]["segments"] = segments
        .map((segment): FlightOffer["slices"][number]["segments"][number] | null => {
          const originCode = segment.origin?.iata_code ?? "";
          const destCode = segment.destination?.iata_code ?? "";
          if (!originCode || !destCode) return null;
          return {
            arrivalTime: segment.arriving_at,
            carrier: segment.operating_carrier?.name ?? segment.marketing_carrier?.name,
            departureTime: segment.departing_at,
            destination: {
              airport: segment.destination?.name,
              city: segment.destination?.city_name,
              country: segment.destination?.country_name,
              iata: destCode,
              terminal: segment.destination?.terminal,
            },
            durationMinutes: parseIsoDurationToMinutes(segment.duration),
            flightNumber:
              segment.marketing_carrier_flight_number ??
              segment.operating_carrier_flight_number,
            marketingCarrier: segment.marketing_carrier?.iata_code,
            operatingCarrier: segment.operating_carrier?.iata_code,
            origin: {
              airport: segment.origin?.name,
              city: segment.origin?.city_name,
              country: segment.origin?.country_name,
              iata: originCode,
              terminal: segment.origin?.terminal,
            },
          };
        })
        .filter((s): s is FlightOffer["slices"][number]["segments"][number] =>
          Boolean(s)
        );

      if (!normalizedSegments.length) return null;
      return {
        cabinClass:
          (slice.cabin_class as FlightOffer["slices"][number]["cabinClass"]) ??
          "economy",
        segments: normalizedSegments,
      };
    })
    .filter((s): s is FlightOffer["slices"][number] => Boolean(s));

  if (!normalizedSlices.length) return null;

  return FLIGHT_OFFER_SCHEMA.parse({
    id: offer.id,
    price: { amount, currency },
    provider: "duffel",
    slices: normalizedSlices,
  });
}

/**
 * Normalize Duffel response JSON into a FlightOffer array and resolved currency.
 */
export function mapDuffelOffersList(
  payload: unknown,
  fallbackCurrency: string
): {
  offers: FlightOffer[];
  currency: string;
  itineraries: Array<{
    id: string;
    price: number;
    segments: Array<{
      arrival?: string;
      carrier?: string;
      departure?: string;
      destination: string;
      flightNumber?: string;
      operatingCarrier?: string;
      origin: string;
    }>;
    bookingUrl?: string;
  }>;
} {
  const data = (payload as { data?: unknown })?.data;
  const offerArray: DuffelOffer[] =
    (Array.isArray((data as { offers?: unknown })?.offers)
      ? (data as { offers: DuffelOffer[] }).offers
      : Array.isArray(data)
        ? (data as DuffelOffer[])
        : []) ?? [];

  const offers = offerArray
    .map((offer) => {
      try {
        return mapDuffelOffer(offer);
      } catch {
        return null;
      }
    })
    .filter((o): o is FlightOffer => Boolean(o));

  const resolvedCurrency =
    offers.find((o) => o.price.currency)?.price.currency ?? fallbackCurrency;

  const itineraries =
    offers.map((offer) => ({
      bookingUrl: undefined,
      id: offer.id,
      price: offer.price.amount,
      segments: offer.slices.flatMap((slice) =>
        slice.segments.map((seg) => ({
          arrival: seg.arrivalTime,
          carrier: seg.carrier ?? seg.marketingCarrier ?? seg.operatingCarrier,
          departure: seg.departureTime,
          destination: seg.destination.iata,
          flightNumber: seg.flightNumber,
          operatingCarrier: seg.operatingCarrier,
          origin: seg.origin.iata,
        }))
      ),
    })) ?? [];

  return { currency: resolvedCurrency, itineraries, offers };
}
