/**
 * @fileoverview Helpers for loading and caching popular hotel destinations.
 */

export type PopularDestinationProps = {
  destination: string;
  priceFrom: number;
  rating: number;
};

export type PopularDestinationApiResponse = {
  city: string;
  country?: string;
  avgPrice?: string;
  imageUrl?: string;
};

export const DEFAULT_POPULAR_DESTINATIONS: PopularDestinationProps[] = [
  { destination: "New York", priceFrom: 199, rating: 4.8 },
  { destination: "Paris", priceFrom: 229, rating: 4.7 },
  { destination: "Tokyo", priceFrom: 179, rating: 4.9 },
  { destination: "London", priceFrom: 249, rating: 4.6 },
  { destination: "Barcelona", priceFrom: 189, rating: 4.8 },
  { destination: "Rome", priceFrom: 219, rating: 4.7 },
];

const POPULAR_DESTINATIONS_BY_CITY = new Map(
  DEFAULT_POPULAR_DESTINATIONS.map((destination) => [
    destination.destination.toLowerCase(),
    destination,
  ])
);

export const POPULAR_DESTINATIONS_CACHE_KEY = "hotelsSearch:popularDestinations";
export const POPULAR_DESTINATIONS_CACHE_TTL_MS = 60 * 60 * 1000;

export function parseAvgPrice(value: string | undefined): number | null {
  if (!value) return null;
  const numeric = Number.parseFloat(value.replace(/[^\d.]/g, ""));
  return Number.isFinite(numeric) && numeric >= 0 ? numeric : null;
}

export function readCachedPopularDestinations(
  storage: Storage,
  nowMs: number
): PopularDestinationProps[] | null {
  try {
    const stored = storage.getItem(POPULAR_DESTINATIONS_CACHE_KEY);
    if (!stored) return null;
    const parsed: unknown = JSON.parse(stored);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("ts" in parsed) ||
      !("destinations" in parsed)
    ) {
      return null;
    }
    const ts = (parsed as { ts: unknown }).ts;
    if (typeof ts !== "number" || nowMs - ts > POPULAR_DESTINATIONS_CACHE_TTL_MS) {
      return null;
    }
    const destinations = (parsed as { destinations: unknown }).destinations;
    if (
      !Array.isArray(destinations) ||
      !destinations.every(
        (item) =>
          typeof item === "object" &&
          item !== null &&
          "destination" in item &&
          "priceFrom" in item &&
          "rating" in item
      )
    ) {
      return null;
    }
    return destinations as PopularDestinationProps[];
  } catch {
    return null;
  }
}

export function writeCachedPopularDestinations(
  storage: Storage,
  nowMs: number,
  destinations: PopularDestinationProps[]
): void {
  try {
    storage.setItem(
      POPULAR_DESTINATIONS_CACHE_KEY,
      JSON.stringify({ destinations, ts: nowMs })
    );
  } catch {
    // ignore
  }
}

export function mapPopularDestinationsFromApiResponse(
  body: unknown
): PopularDestinationProps[] {
  if (!Array.isArray(body)) return [];

  return body
    .filter(
      (item): item is PopularDestinationApiResponse =>
        typeof item === "object" && item !== null && "city" in item
    )
    .map((item) => {
      const city = String(item.city ?? "").trim();
      const fallback = POPULAR_DESTINATIONS_BY_CITY.get(city.toLowerCase());
      const parsedPrice = parseAvgPrice(item.avgPrice);
      return {
        destination: city,
        priceFrom: parsedPrice ?? fallback?.priceFrom ?? 0,
        rating: fallback?.rating ?? 4.6,
      } satisfies PopularDestinationProps;
    })
    .filter((item) => item.destination.length > 0 && item.priceFrom > 0);
}
