/**
 * @fileoverview Thin wrapper around the official Amadeus Node SDK.
 *
 * Provides lazy singleton construction and typed helper methods for the
 * accommodations workload (hotel geocode search, offers search, booking).
 */

import Amadeus from "amadeus";

type AmadeusClient = InstanceType<typeof Amadeus>;

let singleton: AmadeusClient | undefined;

/**
 * Test-only setter to inject a mock Amadeus client and reset the singleton.
 */
export function setAmadeusClientForTests(client: AmadeusClient | null): void {
  singleton = client ?? undefined;
}

/**
 * Retrieves a required environment variable value.
 *
 * @param name - Environment variable name
 * @returns Environment variable value
 * @throws {Error} When environment variable is missing
 */
function getEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable ${name}`);
  }
  return value;
}

/**
 * Returns a singleton Amadeus client instance.
 *
 * Initializes the client on first call using AMADEUS_CLIENT_ID,
 * AMADEUS_CLIENT_SECRET, and AMADEUS_ENV environment variables.
 * Subsequent calls return the same instance.
 *
 * @returns Configured Amadeus client instance
 * @throws {Error} When required environment variables are missing
 */
export function getAmadeusClient(): AmadeusClient {
  if (singleton) return singleton;
  singleton = new Amadeus({
    clientId: getEnv("AMADEUS_CLIENT_ID"),
    clientSecret: getEnv("AMADEUS_CLIENT_SECRET"),
    hostname:
      process.env.AMADEUS_ENV === "production"
        ? "api.amadeus.com"
        : "test.api.amadeus.com",
  });
  return singleton;
}

/**
 * Searches for hotels by geographic coordinates.
 *
 * @param params - Search parameters
 * @param params.latitude - Latitude coordinate (-90 to 90)
 * @param params.longitude - Longitude coordinate (-180 to 180)
 * @param params.radiusKm - Search radius in kilometers (default: 5)
 * @returns Promise resolving to Amadeus API response with hotel data
 */
export function listHotelsByGeocode(params: {
  latitude: number;
  longitude: number;
  radiusKm?: number;
}) {
  const client = getAmadeusClient();
  return client.referenceData.locations.hotels.byGeocode.get({
    latitude: params.latitude,
    longitude: params.longitude,
    radius: params.radiusKm ?? 5,
    radiusUnit: "KM",
  });
}

/**
 * Searches for hotel offers by hotel IDs and stay dates.
 *
 * @param params - Search parameters
 * @param params.hotelIds - Array of Amadeus hotel IDs to search
 * @param params.checkInDate - Check-in date in YYYY-MM-DD format
 * @param params.checkOutDate - Check-out date in YYYY-MM-DD format
 * @param params.adults - Number of adult guests
 * @param params.currency - ISO currency code (default: "USD")
 * @returns Promise resolving to Amadeus API response with hotel offers
 */
export function searchHotelOffers(params: {
  hotelIds: string[];
  checkInDate: string;
  checkOutDate: string;
  adults: number;
  currency?: string;
}) {
  const client = getAmadeusClient();
  return client.shopping.hotelOffersSearch.get({
    adults: params.adults,
    checkInDate: params.checkInDate,
    checkOutDate: params.checkOutDate,
    currency: params.currency ?? "USD",
    hotelIds: params.hotelIds.join(","),
    includeClosed: false,
  });
}

/**
 * Books a hotel offer using the provided booking payload.
 *
 * @param payload - Booking payload containing guest details, hotel offer ID, and payment information
 * @returns Promise resolving to Amadeus API response with booking confirmation
 */
export function bookHotelOffer(payload: Record<string, unknown>) {
  const client = getAmadeusClient();
  return client.booking.hotelBookings.post(JSON.stringify(payload));
}
